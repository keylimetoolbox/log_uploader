#! /usr/bin/python
"""
Module for uploading logs to S3 for Blueprint

To use, configure the variables below for your environment and then add this to a
crontab entry or /etc/cron.daily/ file.

    python blueprint_log_uploader.py

"""
import boto
import os
import traceback
import datetime
import sys
import gzip
from StringIO import StringIO

#
# Configure these for your environment
#

# Your access key and secret for your AWS account,
#
# You can hard-code this here or set it in the environment variables
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

# The bucket we have assigned you
BUCKET = 'yourbucket.ninebyblue'

# A date format specification using strftime format, that will match the dates in your
# log file names.
DATE_FORMAT = '%Y.%m.%d'

# The location of the files to upload
#
# For Windows you might use something like this:
#SOURCE_LOG_DIR = '\\\\SomeServer\\public\\logs\\www\\'
#
# For Unix-like systems it might be something like this:
SOURCE_LOG_DIR = '/var/log/www'

# Number of days ago to find files for by the date in the file name.
# For example, if this is -1, then the script will look for yesterday's files.
DATE_OFFSET = -1

# You should not need to change anything below here.
# ---------------------------------------------------------

class UploadLogFiles():
    def __init__(self):
        if not self.check_connected_to_network():
            print "Exiting..."
            sys.exit(2)
        self.bucket_connection = self.get_bucket()

    def perform(self):
        files = self.clean_file_names(self.bucket_connection, self.determine_files_to_get())
        for file in files:
            try:
                self.download_compress_upload(file, self.bucket_connection)
            except Exception as e:
                print '-' * 10
                print "Unable to upload file '%s'..." % file
                print ' '.join(traceback.format_exception(*sys.exc_info()))
                print '-' * 10

    def check_connected_to_network(self):
        """Determine if you are connected to the intranet and get filenames"""
        if not os.path.isdir(SOURCE_LOG_DIR):
            print """Not able to connect to the log directory (%s). If this is a shared path on another machine make sure
that you are connected to the right network (such as a VPN) and that the machine is running and sharing the
path.""" % SOURCE_LOG_DIR
            return False
        else:
            return True

    def get_bucket(self):
        """Returns the bucket where the log files will be stored."""
        print "Connecting to bucket '%s'..." % BUCKET
        conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        return conn.get_bucket(BUCKET)

    def determine_files_to_get(self):
        """Determines the files to get. Returns a list containing the file names.
        Note that this does *not* descend into subdirectories"""
        date = today = datetime.datetime.today() + datetime.timedelta(days=DATE_OFFSET)
        date_pattern = datetime.date.strftime(date, DATE_FORMAT)
        file_names = [f for f in os.listdir(SOURCE_LOG_DIR) if os.path.isfile(os.path.join(SOURCE_LOG_DIR,f)) and date_pattern in f]
        print file_names
        return file_names

    def clean_file_names(self, bucket, file_names):
        """Skip the files that are already on the Amazon bucket so that they aren't re-downloaded."""
        print "Excluding existing file names..."
        for key in bucket.list():
            for file in file_names:
                if file in key.name:
                  file_names.remove(file)
        print file_names
        return file_names

    def download_compress_upload(self, file, bucket):
        """Given the name of a file, it downloads, compresses, and uploads the file to S3."""
        content = open(os.path.join(SOURCE_LOG_DIR, file))
        print "Opening file %s..." % os.path.join(SOURCE_LOG_DIR, file)
        headers = {'Content-Type': 'text/plain', 'Content-Encoding': 'gzip'}

        if file[-3:] == '.gz':
          key = bucket.new_key(file)
          stream = content
        else:
          key = bucket.new_key('%s.gz' % file)
          stream = StringIO()
          gz = gzip.GzipFile(fileobj=stream, mode='wb', filename=file, compresslevel=9)
          gz.writelines(content)
          gz.close()
          content.close()

        print "Uploading %s to %s..." % (file, key.name)
        stream.seek(0)
        key.set_contents_from_file(stream, headers)
        stream.close()

        # Set ACL
        key.add_user_grant('FULL_CONTROL', '0b2b6d7e33c143cff9616ebaaee4c4670db68853a308b382410a1c0bf2ba2ace')

if __name__ == '__main__':
    UploadLogFiles().perform()
