# AWS MFA Helper

### amh

## Requirement:

 - python3
 - boto3
 - AWS credentials file (see below)

### AWS credentials

#### Target Profile
aws_mfa_helper suppose that you already have the target profile setup into .aws/credentials

if it's not the case add to the .aws/credentials something like

```ini
[initial-assume-role-call]
region = eu-west-2
aws_access_key_id =
aws_secret_access_key =
aws_session_token =
expiration =

[an-other-profile]
role_arn = arn:aws:iam::<an assume role ARN>
source_profile = initial-assume-role-call
region = eu-west-2
```

Value for aws_* and expiration in `initial-assume-role-call` doesn't matter as they will be overwritten

#### Login profile

`.aws/credentials` file must have a valid profile setup to query the mfa devices and request a token
It's usually the profile that will return your user ARN from `get-caller-id`
```console
aws --profile <login_profile> sts get-caller-identity
```
should return
```console
{
    "UserId": "ABCDEFGHIJKLM",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/..."
}

```

### Usage

* First backup your credetial file
```console
cp ~/.aws/credentials ~/.aws/credentials.`date -I`
```

The script try to restore the original `.aws/credential` file in case of error but it's not bulletproof

#### List all the profiles in `.aws/credential`
```console
python3 amh.py -l
```

#### List the mfa devices
```console
python3 amh.py --login-profile <login profile> --list-mfa-devices

```

#### Get a 1 hour token

```console
python3 amh.py \
        --login-profile <login profile> \
        --serial-number <mfa serial number> \
        --get-session-token \
        --target-profile initial-assume-role-call --test
```

#### Get the maximum duration token (default 36 hours)

```console
python3 amh.py \
        --login-profile <login profile> \
        --serial-number <mfa serial number> \
        --get-session-token \
        --target-profile initial-assume-role-call
```

### Config File

The parameters necessary to get a new token and update the `.aws/credential` file
can be stored in a config file (in json format) using the `--config-write` option.

```console
python3 amh.py \
        --login-profile <login profile> \
        --serial-number <mfa serial number> \
        --get-session-token \
        --target-profile initial-assume-role-call \
        --config-write
```

* The following calls can then be simplified
```console
python3 amh.py --get-session-token
```

* The default config file is `~/.aws_mfa_helper.json`
* Default config can be changed using `--config  <path to config file>` option
* Options set on the command line will take precedence over the config file

```
```

### Help

```console
usage: amh.py [-h]
                         [-l] [--list-mfa-devices]
                         [--login-profile LOGIN_PROFILE] [--serial-number SERIAL_NUMBER]
                         [--duration-seconds DURATION_SECONDS]
                         [--get-session-token] [--target-profile TARGET_PROFILE] [--test]
                         [--config CONFIG] [--config-write]


optional arguments:
  -h, --help            show this help message and exit

  -l, --list-file-profiles
                        list profiles stored in .aws/credential

  --login-profile LOGIN_PROFILE
                        profile linked with your mfa device

  --list-mfa-devices    list the mfa devices linked with the login profile

  --serial-number SERIAL_NUMBER
                        one of the mfa serial number returned by list-mfa-devices

  --duration-seconds DURATION_SECONDS
                        token duration

  --test                reduce the token duration to 1h only for testing

  --get-session-token   get a temporary credentials

  --target-profile TARGET_PROFILE
                        profile where the new token will be stored

  --config CONFIG       (json format) config file path, see --config-write

  --config-write        write a json config file with the value from the cli arguments

```
