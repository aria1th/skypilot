# Sky

![pytest](https://github.com/sky-proj/sky/actions/workflows/pytest.yml/badge.svg)

Sky is a framework to run any workload seamlessly across different cloud providers through a unified interface. No knowledge of cloud offerings is required or expected – you simply define the workload and its resource requirements, and Sky will automatically execute it on AWS, Google Cloud Platform or Microsoft Azure.

<!-- TODO: We need a logo here -->
## A Quick Example
The following command can automatically spin up a cluster on the cheapest available cloud fulfilled the required resources, setup and run the commands in the `hello_sky.yaml`
```bash
sky launch -c mycluster hello_sky.yaml
```

```yaml
# hello_sky.yaml

resources:
  # Optional; if left out, pick from the available clouds.
  cloud: aws

  accelerators: V100:1 # 1x NVIDIA V100 GPU

# Working directory (optional) containing the project codebase.
# This directory will be synced to ~/sky_workdir on the provisioned cluster.
workdir: .

# Typical use: pip install -r requirements.txt
setup: |
  echo "running setup"

# Typical use: make use of resources, such as running training.
run: |
  echo "hello sky!"
  conda env list
```

## Getting Started
Please refer to our [documentation](https://sky-proj-sky.readthedocs-hosted.com/en/latest/).
- [Installation](https://sky-proj-sky.readthedocs-hosted.com/en/latest/getting-started/installation.html)
- [Quickstart](https://sky-proj-sky.readthedocs-hosted.com/en/latest/getting-started/quickstart.html)
- [Sky CLI](https://sky-proj-sky.readthedocs-hosted.com/en/latest/reference/cli.html)

### Installation

```bash
# Sky requires python >= 3.6 and < 3.10.
git clone ssh://git@github.com/sky-proj/sky.git
cd sky
pip install ".[all]"
```

Sky currently supports three major cloud providers: AWS, GCP, and Azure.  If you
only have access to certain clouds, use any combination of `".[aws,azure,gcp]"`
(e.g., `".[aws,gcp]"`) to reduce the dependencies installed.

### Cloud Account Setup

To run tasks in the clouds, configure access to at least one cloud:

**AWS**

To get the **AWS Access Key** required by `aws configure`, please refer to the [AWS manual](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_CreateAccessKey). The **Default region name [None]:** and **Default output format [None]:** fields are optional and can be left blank to choose defaults.

```bash
# Install boto
pip install boto3

# Configure your AWS credentials
aws configure
```

**GCP**

```bash
pip install google-api-python-client
conda install -c conda-forge google-cloud-sdk

# Init.
gcloud init

# Run this if you don't have a credentials file.
# This will generate ~/.config/gcloud/application_default_credentials.json.
gcloud auth application-default login
```

**Azure**

```bash
# Install the Azure CLI
pip install azure-cli==2.30.0
# Login
az login
# Set the subscription to use
az account set -s <subscription_id>
```

**Verifying cloud setup**

After configuring the desired clouds, you can optionally run `sky check` to verify that credentials are correctly set up:

```bash
sky check
```

This will produce a summary like:

```
Checking credentials to enable clouds for Sky.
  AWS: enabled
  GCP: enabled
  Azure: enabled

Sky will use only the enabled clouds to run tasks. To change this, configure cloud credentials, and run sky check.
```

## Developer Guide
### Setup

```bash
# Sky requires python >= 3.6 and < 3.10.
# You can just install the dependencies for
# certain clouds, e.g., ".[aws,azure,gcp]"
pip install -e ".[all]"
```

### Some general engineering practice suggestions

These are suggestions, not strict rules to follow. For general coding style, follow [google style guide](https://google.github.io/styleguide/pyguide.html).

* Use `TODO(author_name)`/`FIXME(author_name)` instead of blank `TODO/FIXME`. This is critical for tracking down issues. You can write TODOs with your name and assign it to others (on github) if it is someone else's issue.
* Delete your branch after merging it. This keeps the repo clean and faster to sync.
* Use an exception if this is an error. Only use `assert` for debugging or proof-checking purpose. This is because exception messages usually contain more information.
* Use modern python features and styles that increases code quality.
  * Use f-string instead of `.format()` for short expressions to increase readability.
  * Use `class MyClass:` instead of `class MyClass(object):`. The later one was a workaround for python2.x.
  * Use `abc` module for abstract classes to ensure all abstract methods are implemented.
  * Use python typing. But you should not import external objects just for typing. Instead, import typing-only external objects under `if typing.TYPE_CHECKING:`.