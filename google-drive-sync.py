#!/usr/bin/env python3
import argparse
import datetime
import io
import logging
import os
import time

import google.auth
from google.auth.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class GoogleDrive:
    _creds: Credentials
    _files_service: Resource

    def __init__(self) -> None:
        logging.debug("Initialising google drive client")

        self._creds, _ = google.auth.default()

        # pylint: disable=maybe-no-member
        self._files_service = build("drive", "v3", credentials=self._creds).files()

    def get_modification_time(self, file_id: str) -> float:
        file = self._files_service.get(
            fileId=file_id,
            fields="modifiedTime",
        ).execute()

        modification_time = file["modifiedTime"]

        if not isinstance(modification_time, str):
            raise ValueError(
                f"Modification time of {file_id} is not int: "
                f"{modification_time} ({type(modification_time)})"
            )

        return datetime.datetime.strptime(modification_time, TIME_FORMAT).timestamp()

    def download(self, file_id: str) -> bytes:
        logging.debug("Downloading %s", file_id)

        request = self._files_service.get_media(fileId=file_id)

        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)

        while not downloader.next_chunk()[1]:
            pass

        return file.getvalue()

    def upload(self, path: str, file_id: str) -> None:
        logging.debug("Uploading %s to %s", path, file_id)

        media_body = MediaFileUpload(path, resumable=True)

        updated_file = self._files_service.update(
            fileId=file_id,
            body={
                "modifiedTime": datetime.datetime.strftime(
                    datetime.datetime.fromtimestamp(os.path.getmtime(path)),
                    TIME_FORMAT,
                )
            },
            media_body=media_body,
        ).execute()
        return updated_file


class SyncFile:
    _drive: GoogleDrive
    _local_path: str
    _remote_file_id: str

    def __init__(self, local_path: str, remote_file_id: str) -> None:
        self._drive = GoogleDrive()
        self._local_path = local_path
        self._remote_file_id = remote_file_id

    def _get_local_modification_time(self) -> float:
        return os.path.getmtime(self._local_path)

    def _get_remote_modification_time(self) -> float:
        return self._drive.get_modification_time(self._remote_file_id)

    def _upload(self) -> None:
        self._drive.upload(self._local_path, self._remote_file_id)

    def _download(self) -> None:
        content = self._drive.download(self._remote_file_id)

        with open(self._local_path, "wb") as file:
            file.write(content)

    def sync(self) -> None:
        # float(int()) to get rid of sub-integer precision, which
        # doesn't match across filesystem and google drive
        local_modification_time = float(int(self._get_local_modification_time()))
        logging.debug(
            "Local modification time of %s: %s",
            self._local_path,
            local_modification_time,
        )

        remote_modification_time = float(int(self._get_remote_modification_time()))
        logging.debug(
            "Remote modification time of %s: %s",
            self._remote_file_id,
            remote_modification_time,
        )

        if local_modification_time > remote_modification_time:
            self._upload()
        elif local_modification_time < remote_modification_time:
            self._download()
        else:
            logging.debug(
                "Remote %s and local %s files have the same timestamp, doing nothing",
                self._remote_file_id,
                self._local_path,
            )


def main() -> None:
    # pip install google-api-python-client
    # gcloud auth revoke
    # gcloud auth login --enable-gdrive-access
    # export GOOGLE_APPLICATION_CREDENTIALS=${HOME}/.config/gcloud/legacy_credentials/<email>/adc.json

    logging.getLogger().setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(
        description=(
            "Synchronise specified files the with "
            "corresponding Google Drive documents"
        )
    )
    parser.add_argument(
        "-s",
        "--sync",
        help="Local file path and Google Drive file id separated by comma",
        required=True,
        type=str,
        action="append",
    )
    parser.add_argument(
        "-i",
        "--interval",
        help="How often to check for changes (in seconds)",
        required=False,
        type=int,
        default=10,
    )
    args = parser.parse_args()

    sync_pairs = args.sync

    while True:
        for sync_pair in sync_pairs:
            local_path, remote_id = sync_pair.split(",")

            sync = SyncFile(local_path, remote_id)
            sync.sync()

        logging.info("Sync done, waiting %s seconds", args.interval)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
