"""Assumptions:

- Users supply a time estimator func for each node in the DAG.
- Assuming homogeneous instances:
  - Support for choosing # instances
- Support for heterogeneous instances?


Optimization problem:
 - min cost, subject to some constraints?
 - min latency, subject to some constraints?

DAG assumption: chain.  If multiple branches, take into account of parallelism?

Incorporate the notion of region/zone (affects pricing).
Incorporate the notion of per-account egress quota (affects pricing).
"""
import textwrap
import sky

import time_estimators

CLUSTER_NAME = 'test-chain-app-b'
# CLUSTER_NAME = 'profile-tpu'

SETUP = 'echo running setup'

PROC_SETUP = textwrap.dedent("""\
        wget https://s3.amazonaws.com/amazon-reviews-pds/tsv/amazon_reviews_us_Books_v1_02.tsv.gz
        tar xvzf amazon_reviews_us_Books_v1_02.tsv.gz
        """)
PROC_RUN = 'echo processing; echo generated_data > OUTPUTS[0]/dataset.txt'

TRAIN_RUN = 'cat INPUTS[0]/dataset.txt; echo training; echo trained_model > OUTPUTS[0]/model.txt'

INFER_RUN = 'cat INPUTS[0]/model.txt; echo inference DONE.'


def make_application():
    """A simple application: train_op -> infer_op."""

    with sky.Dag() as dag:
        # Preprocess.
        proc_op = sky.Task('proc_op', setup=PROC_SETUP, run=PROC_RUN)
        # input can be downloaded with wget, so no input need to be set
        proc_op.set_outputs('CLOUD://skypilot-pii-annonymized-dataset',
                            estimated_size_gigabytes=1)

        proc_resources = {sky.Resources(sky.Azure(), 'Standard_DC8_v2')}
        proc_op.set_resources(proc_resources)
        proc_op.set_time_estimator(lambda _: 0.6)

        # Train.
        train_op = sky.Task(
            'train_op',
            setup=SETUP,
            run=TRAIN_RUN,
        )
        # inputs_outputs_on_bucket=True)

        train_op.set_inputs(
            proc_op.get_outputs(),
            estimated_size_gigabytes=1,
        )

        # 'CLOUD': saves to the cloud this op ends up executing on.
        train_op.set_outputs('CLOUD://skypilot-pipeline-b-model',
                             estimated_size_gigabytes=0.1)

        train_resources = {
            sky.Resources(sky.AWS(), 'p3.2xlarge'),  # 1 V100, EC2.
            sky.Resources(sky.AWS(), 'p3.8xlarge'),  # 4 V100s, EC2.
            sky.Resources(sky.GCP(), accelerators={'V100': 1}),  # 1 V100s, GCP.
            sky.Resources(sky.GCP(), accelerators={'V100': 4}),  # 4 V100s, GCP.
            # Tuples mean all resources are required.
            sky.Resources(sky.GCP(), 'n1-standard-8', 'tpu-v3-8'),
        }
        train_op.set_resources(train_resources)

        # TODO(zhwu): time estimator for BERT
        train_op.set_time_estimator(time_estimators.resnet50_estimate_runtime)

        # Infer.
        infer_op = sky.Task('infer_op', setup=SETUP, run=INFER_RUN)

        # Data dependency.
        # FIXME: make the system know this is from train_op's outputs.
        infer_op.set_inputs(train_op.get_outputs(),
                            estimated_size_gigabytes=0.1)

        # NOTE(zhwu): Have to add use_spot here, since I only have spot quota
        # for inf instances
        infer_op.set_resources({
            sky.Resources(sky.AWS(), 'inf1.2xlarge', use_spot=True),
            sky.Resources(sky.AWS(), 'p3.2xlarge', use_spot=True),
            sky.Resources(sky.GCP(), 'n1-standard-4', 'T4', use_spot=True),
            sky.Resources(sky.GCP(), 'n1-standard-8', 'T4', use_spot=True),
        })

        # TODO(zhwu): time estimator for BERT
        infer_op.set_time_estimator(
            time_estimators.resnet50_infer_estimate_runtime)

        # # Chain the tasks (Airflow syntax).
        # # The dependency represents data flow.
        proc_op >> train_op
        train_op >> infer_op

    return dag


dag = make_application()
sky.execution._launch_chain(dag,
                            cluster_name=CLUSTER_NAME,
                            retry_until_up=True,
                            dryrun=False)