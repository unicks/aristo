import requests
import os
import argparse
import json

# Configuration
MOODLE_URL = "https://aristoplan.moodlecloud.com"
MOODLE_TOKEN = "c254f0acadf572f82f74dc03ea7ca156"
DOWNLOAD_DIR = "downloads"

def call_moodle_api(function, params=None):
    if params is None:
        params = {}
    params.update({
        'wstoken': MOODLE_TOKEN,
        'moodlewsrestformat': 'json',
        'wsfunction': function
    })
    response = requests.post(f"{MOODLE_URL}/webservice/rest/server.php", data=params)
    response.raise_for_status()
    return response.json()

def list_courses():
    courses = call_moodle_api('core_enrol_get_users_courses', {'userid': 2})  # Change userid as needed
    for course in courses:
        print(f"{course['id']}: {course['fullname']}")

def list_assignments(courseid):
    data = call_moodle_api('mod_assign_get_assignments', {'courseids[0]': courseid})
    for course in data['courses']:
        for assign in course['assignments']:
            print(f"{assign['id']}: {assign['name']}")

def list_submissions(assignid):
    data = call_moodle_api('mod_assign_get_submissions', {'assignmentids[0]': assignid})
    for submission in data['assignments'][0]['submissions']:
        print(f"User {submission['userid']} - Status: {submission['status']}")

def download_all_submissions(assignid):
    data = call_moodle_api('mod_assign_get_submissions', {'assignmentids[0]': assignid})
    submissions = data['assignments'][0]['submissions']
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    for submission in submissions:
        for plugin in submission.get('plugins', []):
            if plugin['type'] == 'file':
                for filearea in plugin['fileareas']:
                    for file in filearea['files']:
                        fileurl = file['fileurl']
                        # Use correct token via header or URL param
                        download_url = f"{fileurl}?token={MOODLE_TOKEN}"

                        filename = os.path.join(DOWNLOAD_DIR, f"user_{submission['userid']}_{file['filename']}")
                        print(f"Downloading {filename}...")

                        response = requests.get(download_url, stream=True)
                        if response.status_code == 200:
                            with open(filename, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        else:
                            print(f"Failed to download {filename} – status {response.status_code}")


def grade_students(assignid, grades_json):
    """
    Grade students for a given assignment.
    grades_json: list of dicts, each with 'userid', 'grade', and optional 'comment'
    Example:
    [
        {"userid": 5, "grade": 90, "comment": "Great job!"},
        {"userid": 6, "grade": 75}
    ]
    """
    grade_items = []
    for entry in grades_json:
        item = {
            'userid': entry['userid'],
            'grade': entry['grade'],
            'attemptnumber': -1,  # -1 means latest
            'addattempt': 0,
            'workflowstate': '',
            'plugindata': {}
        }
        if 'comment' in entry:
            item['plugindata']['assignfeedbackcomments_editor'] = {
                'text': entry['comment'],
                'format': 1
            }
        grade_items.append(item)

    params = {
        'assignmentid': assignid,
        'applytoall': 0
    }
    for idx, item in enumerate(grade_items):
        for key, value in item.items():
            if isinstance(value, dict):
                for subkey, subval in value.items():
                    if isinstance(subval, dict):
                        for subsubkey, subsubval in subval.items():
                            params[f'grades[{idx}][{key}][{subkey}][{subsubkey}]'] = subsubval
                    else:
                        params[f'grades[{idx}][{key}][{subkey}]'] = subval
            else:
                params[f'grades[{idx}][{key}]'] = value

    result = call_moodle_api('mod_assign_save_grades', params)
    print("Grades submitted:", result)


def main():
    parser = argparse.ArgumentParser(description="Moodle CLI Tool")
    subparsers = parser.add_subparsers(dest='command')

    parser_courses = subparsers.add_parser('list-courses')
    parser_assignments = subparsers.add_parser('list-assignments')
    parser_assignments.add_argument('courseid', type=int)
    parser_submissions = subparsers.add_parser('list-submissions')
    parser_submissions.add_argument('assignid', type=int)
    parser_download = subparsers.add_parser('download-submissions')
    parser_download.add_argument('assignid', type=int)
    parser_grade = subparsers.add_parser('grade-students')
    parser_grade.add_argument('assignid', type=int)
    parser_grade.add_argument('grades_json', type=str, help='Grades JSON string or path to JSON file')

    args = parser.parse_args()
    if args.command == 'list-courses':
        list_courses()
    elif args.command == 'list-assignments':
        list_assignments(args.courseid)
    elif args.command == 'list-submissions':
        list_submissions(args.assignid)
    elif args.command == 'download-submissions':
        download_all_submissions(args.assignid)
    elif args.command == 'grade-students':
        # Try to load as file, else parse as JSON string
        if os.path.isfile(args.grades_json):
            with open(args.grades_json, 'r', encoding='utf-8') as f:
                grades = json.load(f)
        else:
            grades = json.loads(args.grades_json)
        grade_students(args.assignid, grades)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()