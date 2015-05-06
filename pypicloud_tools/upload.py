"""PyPICloud uploader tool to bypass PyPICloud and send directly to S3.

Copyright (c) 2015 CCP Games. Released for use under the MIT license.
"""


from __future__ import print_function

import os
import math
import requests
from filechunkio import FileChunkIO
from concurrent.futures import ThreadPoolExecutor

from . import print_dot, get_settings, get_bucket_conn


def _upload_chunk(bucket, mp_id, part_num, filename, offset, bytes, retries=3):
    """Uploads a single chunk, with retries."""

    try:
        for mp in bucket.get_all_multipart_uploads():
            if mp.id == mp_id:
                with FileChunkIO(filename, "rb", offset=offset, bytes=bytes) as fp:
                    mp.upload_part_from_file(fp=fp, part_num=part_num, cb=print_dot)
                break
    except Exception as error:
        if retries:
            _upload_chunk(bucket, mp_id, part_num, filename, offset, bytes,
                          retries=retries - 1)
        else:
            print("{} failed!".format(part_num))
            raise error
    else:
        print(part_num, end="")


def upload_file(filename, bucket, s3_config):
    """Uploads a file by relative path into the connected bucket object."""

    source_size = os.stat(filename).st_size
    headers = {"Content-Type": "application/octet-stream"}

    chunk_size = 5242880  # 50MB chunks
    bytes_per_chunk = max(int(math.sqrt(chunk_size) * math.sqrt(source_size)),
                          chunk_size)
    num_chunks = int(math.ceil(source_size / float(bytes_per_chunk)))

    # determine the key name from the filename
    base_name = os.path.basename(filename).rsplit("-")[0]
    key_name = "{}/{}".format(base_name, os.path.basename(filename))
    mp = bucket.initiate_multipart_upload(key_name, headers=headers)

    print("Uploading {} ...".format(key_name), end="")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i in range(num_chunks):
            offset = i * bytes_per_chunk
            remaining_bytes = source_size - offset
            bytes = min([bytes_per_chunk, remaining_bytes])
            part_num = i + 1
            pool.submit(_upload_chunk, bucket, mp.id, part_num, filename,
                        offset, bytes)

    if len(mp.get_all_parts()) == num_chunks:
        mp.complete_upload()
        if s3_config.acl:
            key = bucket.get_key(key_name)
            key.set_acl(s3_config.acl)
        print(" done!".format(key_name, bucket.name))
    else:
        mp.cancel_upload()
        print(" failed! :(")


def update_cloud(pypi):
    """Updates the index on PyPICloud after uploading to S3 behind its back.

    Args:
        pypi: a PyPIConfig object

    Returns:
        boolean of successfully triggering a refresh of the PyPI index
    """

    # We have to convert from /pypi/ or /simple/ to /admin/
    base_url = pypi.server
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    if base_url.endswith("pypi") or base_url.endswith("simple"):
        base_url = base_url.rsplit("/", 1)[0]

    resp = requests.get(
        "{}/admin/rebuild".format(base_url),
        auth=requests.auth.HTTPBasicAuth(pypi.user, pypi.password)
    )
    resp.raise_for_status()
    return resp.ok


def main():
    """Main command line entry point for uploading."""

    settings = get_settings(upload=True)

    bucket = get_bucket_conn(settings.s3)

    for file in settings.items:
        try:
            upload_file(file, bucket, settings.s3)
        except Exception as error:
            print("Error uploading {}: {}".format(file, error), file=sys.stderr)
            break
    else:
        update_cloud(settings.pypi)  # this raises on HTTP error
        print("PyPICloud server at {} updated".format(settings.pypi.server))


if __name__ == "__main__":
    main()
