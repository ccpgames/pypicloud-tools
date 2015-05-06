# pypicloud-tools

Tools to bypass a PyPICloud installation and communicate directly with S3


## Utilities

### Upload

Uploads file(s) to the PyPICloud S3 bucket directly and performs an admin API call to rebuild the PyPICloud index after.

### Download

Downloads the latest or a specific version directly from S3. Does not talk to PyPICloud and does not install the downloaded package. You can use pip to do either/both of those things.

Also possible with the download command is the `--url` flag to only print a download URL (usable for 5 minutes).

By default, if there are multiple releases of the same package+release, download will prefer wheels, then eggs, then source distributions. You can override that behavior with the `--egg` and `--src` flags.

### List

Lists a package's releases, or releases of a package at a specific version. Again, talks straight to S3 and bypasses the PyPICloud installation.


## Installation

### Simple

```bash
$ pip install pypicloud-tools
```

### From source

```bash
$ git clone https://github.com/ccpgames/pypicloud-tools.git
$ cd pypicloud-tools
$ python setup.py install
```


## Configuration

Configuration for pypicloud-tools piggybacks on your `~/.pypirc` file. You can specify an alternate config file with the `--config` flag, but it must be in the same syntax. That syntax is:

```conf
[pypicloud]
    repository:http://your.pypicloud.server/pypi
    username:admin
    password:hunter7
    bucket:your_bucket
    access:some_key
    secret:other_key
    acl:optional_acl
```

The key **must** be `pypicloud`, it is the only key pypicloud-tools will look at. The username/password combination should have admin credentials on the PyPICloud installation as it needs to call `/admin/rebuild` after a succesful upload.
