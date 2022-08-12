"""Flask inference server.

Implements a Flask server that handles inference requests for some input via a HTTP handler.
To run the server, run the following command from the root directory:
`FLASK_APP=examples/inference_server/server.py flask run`
"""

import os
import pathlib
import random
import re
import string
import subprocess

import flask
import sky
from werkzeug import utils

import inference

LOCAL_UPLOAD_FOLDER = os.path.abspath("examples/inference_server/uploads/")
REMOTE_UPLOAD_FOLDER = '/remote/path/to/folder'
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}

app = flask.Flask(__name__)
app.config['UPLOAD_FOLDER'] = LOCAL_UPLOAD_FOLDER


def run_output(cmd: str, **kwargs) -> str:
    completed_process = subprocess.run(cmd,
                                       stdout=subprocess.PIPE,
                                       shell=True,
                                       check=True,
                                       **kwargs)
    return completed_process.stdout.decode("ascii").strip()


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def run_inference():
    if flask.request.method == 'POST':
        image = flask.request.files['file']
        if not image or not allowed_file(image.filename):
            flask.abort(400, "Invalid image upload")

        filename = utils.secure_filename(image.filename)
        local_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        remote_image_path = os.path.join(REMOTE_UPLOAD_FOLDER, filename)

        pathlib.Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
        image.save(local_image_path)

        with sky.Dag() as dag:
            workdir = os.path.dirname(os.path.abspath(__file__))
            task_name = 'inference_task'
            setup = 'pip3 install --upgrade pip'
            run_fn = f'python inference.py {remote_image_path}'

            task = sky.Task(name=task_name,
                            setup=setup,
                            workdir=workdir,
                            run=run_fn)

            resources = sky.Resources(cloud=sky.Azure())
            task.set_resources(resources)
            task.set_file_mounts({
                # Copy model weights to the cluster
                # Instead of local path, can also specify a cloud object store URI
                '/remote/path/to/model-weights': 'local/path/to/model-weights',
                # Copy image to the cluster
                remote_image_path: local_image_path,
            })

        cluster_name = f'inference-cluster-{" ".join(random.choice(string.ascii_lowercase) for _ in range(10))}'
        sky.launch(
            dag,
            cluster_name=cluster_name,
            detach_run=True,
        )

        cmd_output = run_output(f'sky logs {cluster_name}')
        inference_result = re.findall(
            f'{inference.INFERENCE_RESULT_MARKER}((?:[^\n])+)', cmd_output)

        # Down the cluster in the background
        subprocess.Popen(f'sky down -y {cluster_name}', shell=True)

        return {'result': inference_result}
    elif flask.request.method == 'GET':
        return '''
            <title>Upload Image</title>
            <h1>Upload Image</h1>
            <form method=post enctype=multipart/form-data>
            <input type=file name=file>
            <input type=submit value=Upload>
            </form>
            '''