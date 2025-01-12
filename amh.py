"""
Copyright 2024, 2025 Ali Bendriss

This program is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>.
"""

import os
import argparse
import boto3
import fileinput
import getpass
import json

home = os.path.expanduser('~')
aws_credentials_file = os.path.join(os.path.join(home, '.aws'), 'credentials')
default_config = os.path.join(home, '.aws_mfa_helper.json')

def list_file_profile(acf):
    with open(acf, 'r') as acf_fd:
        for l in acf_fd:
            l = l.strip()
            if l and l.startswith('['):
                print (l)

"""
equivalent to aws --profile <login-profile> iam list-mfa-devices
"""
def list_mfa_devices(profile=''):
    session = boto3.Session(profile_name=profile)
    iam_client = session.client('iam')
    response = iam_client.list_mfa_devices()
    print ("{:<40} {:<40} {}".format('UserName', 'SerialNumber', 'EnableDate'))
    for mfadevices in response['MFADevices']:
        mfa_user = mfadevices['UserName'] if 'UserName' in mfadevices else ''
        mfa_serial = mfadevices['SerialNumber'] if 'UserName' in mfadevices else ''
        mfa_enable_date = mfadevices['EnableDate'] if 'EnableDate' in mfadevices else ''
        print ("{:<40} {:<40} {}".format(mfa_user, mfa_serial, mfa_enable_date))

"""
update aws credential file
"""
def update_aws_credentials_file (acf, profile, session_token):
    credential = session_token['Credentials'] if 'Credentials' in session_token else '{}'
    aws_access_key_id = credential['AccessKeyId'] if 'AccessKeyId' in credential else ''
    aws_session_token = credential['SessionToken'] if 'SessionToken' in credential else ''
    aws_secret_access_key = credential['SecretAccessKey'] if 'SecretAccessKey' in credential else ''
    expiration = credential['Expiration'] if 'Expiration' in credential else ''

    profile_block_begin = False
    profile_block_end = False
    is_profile_block = False
    try:
        with fileinput.input(files=acf, inplace=True) as f:
            for line in f:
                line = line.strip()
                if line.startswith('[{}'.format(profile.strip())):
                    profile_block_begin = True
                    is_profile_block = True if profile_block_begin and not profile_block_end else False
                elif line.startswith('['):
                    profile_block_end = True if profile_block_begin else False
                    is_profile_block = True if profile_block_begin and not profile_block_end else False

                if is_profile_block:
                    if line.startswith('aws_access_key_id'):
                        print ("{} = {}".format ('aws_access_key_id', aws_access_key_id))
                    elif line.startswith('aws_secret_access_key'):
                        print ("{} = {}".format ('aws_secret_access_key', aws_secret_access_key))
                    elif line.startswith('aws_session_token'):
                        print ("{} = {}".format ('aws_session_token', aws_session_token))
                    elif line.startswith('expiration'):
                        print ("{} = {}".format ('expiration', expiration))
                    else:
                        print(line)

                else:
                    print(line)
    except Exception as e:
        if os.path.exists ('{}.bak',format (acf)):
            os.rename('{}.bak',format (acf), acf)


"""
equivalent to aws --profile <login-profile> sts get-session-token \
                  --duration-seconds <duration-seconds> \
                  --serial-number <serial-number>
                  --token-code <asked token code>
return a session-token in json format
"""
def get_session_token (profile, duration_seconds, serial_number):
    assert profile, "empty profile"
    assert int(duration_seconds) > 0, "invalid duration_seconds"
    assert serial_number, "empty serial_number"
    verif_code = getpass.getpass (prompt="Verification Code: ")
    assert verif_code.strip(), "empty verification code"
    session = boto3.Session(profile_name=profile)
    sts_client = session.client('sts')
    response = sts_client.get_session_token(
        DurationSeconds=duration_seconds,
        SerialNumber=serial_number,
        TokenCode=verif_code
    )
    if 'Credentials' in response:
        return response
    else:
        print (response)
        return "{}"

class Config:

    def __init__(self):
        self.login_profile = None
        self.target_profile = None
        self.serial_number = None
        self.duration_seconds = None

    def to_json(self):
        result = {}
        result['aws_mfa_helper'] = {}
        result['aws_mfa_helper']['login_profile'] = self.login_profile
        result['aws_mfa_helper']['target_profile'] = self.target_profile
        result['aws_mfa_helper']['serial_number'] = self.serial_number
        result['aws_mfa_helper']['duration_seconds'] = self.duration_seconds
        result = json.dumps(result, separators=(',', ':'))
        return result

    def from_json (self, src):
        result = json.loads(src)
        if 'aws_mfa_helper' in result:
            result = result['aws_mfa_helper']
            self.login_profile = result['login_profile'] if 'login_profile' in result else None
            self.target_profile = result['target_profile'] if 'target_profile' in result else None
            self.serial_number = result['serial_number'] if 'serial_number' in result else None
            self.duration_seconds = result['duration_seconds'] if 'duration_seconds' in result else None
        return self

    def file_read (self, path):
        result = None
        with open (path) as f:
            result = f.readlines(1024)
        return self.from_json(''.join(result))

    def file_write (self, path):
        result = self.to_json()
        with open (path, 'w') as f:
            f.write(result)
        return self

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument ('-l', '--list-file-profiles',
                         help='list profiles stored in .aws/credential', action='store_true')
    parser.add_argument ('--login-profile', help='profile linked with your mfa device')
    parser.add_argument ('--list-mfa-devices',
                         help='list the mfa devices linked with the login profile', action='store_true')
    parser.add_argument ('--serial-number',
                         help='one of the mfa serial number returned by list-mfa-devices')
    parser.add_argument ('--duration-seconds', help='token duration', type=int, default=129600)
    parser.add_argument ('--test',
                         help='reduce the token duration to 1h only for testing', action='store_true')
    parser.add_argument ('-t', '--get-session-token', help='get a temporary credentials', action='store_true')
    parser.add_argument ('--target-profile', help='profile where the new token will be stored')
    parser.add_argument ('--config',
                         help='(json format) config file path, see --config-write', default=default_config)
    parser.add_argument ('--config-write', help='write a json config file with the value from the cli arguments', action='store_true')

    args = parser.parse_args()
    duration = args.duration_seconds if not args.test else 3600

    if args.list_file_profiles:
        list_file_profile(aws_credentials_file)
    elif args.list_mfa_devices:
        assert args.login_profile, "login_profile not set"
        list_mfa_devices(profile=args.login_profile)
    elif args.get_session_token:
        c = Config()
        if args.config and os.path.exists(args.config):
            c.file_read (args.config)
        c.login_profile = args.login_profile if args.login_profile else c.login_profile
        c.serial_number = args.serial_number if args.serial_number else c.serial_number
        c.target_profile = args.target_profile if args.target_profile else c.target_profile
        c.duration_seconds = duration if args.duration_seconds else c.duration_seconds
        assert c.login_profile, "login_profile not set"
        assert c.serial_number, "serial_number  not set"
        assert c.target_profile, "target_profile not set"
        assert c.target_profile != c.login_profile, "target_profile must not be a login_profile"
        if args.config_write:
            c.file_write(args.config)
        else:
            token = get_session_token (
                profile=c.login_profile,
                duration_seconds=c.duration_seconds,
                serial_number=c.serial_number
            )
            update_aws_credentials_file (
                acf=aws_credentials_file,
                profile=c.target_profile,
                session_token=token
            )
    else:
        print ("""
        AWS MFA Helper
        amh  Copyright (C) 2025  Ali Bendriss
        This program comes with ABSOLUTELY NO WARRANTY;
        This is free software, and you are welcome to redistribute it
        under certain conditions;
        """)
        
        parser.print_help()
