import json

import pytest

from mycloud.cli import main


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point every test at an empty config dir and clear property env vars."""
    monkeypatch.setenv("MYCLOUD_CONFIG", str(tmp_path))
    for var in ("MYCLOUD_CORE_PROJECT", "MYCLOUD_COMPUTE_ZONE", "MYCLOUD_CORE_DISABLE_PROMPTS"):
        monkeypatch.delenv(var, raising=False)


def mycloud(capsys, *argv):
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def configured(capsys):
    mycloud(capsys, "config", "set", "project", "demo")
    mycloud(capsys, "config", "set", "compute/zone", "us-east1-b")


def test_version(capsys):
    code, out, _ = mycloud(capsys, "version")
    assert code == 0
    assert out.startswith("mycloud ")


def test_missing_project_explains_the_fix(capsys):
    code, out, err = mycloud(capsys, "compute", "instances", "list")
    assert code == 1
    assert out == ""
    assert "ERROR: (mycloud.compute.instances.list)" in err
    assert "mycloud config set core/project" in err


def test_property_precedence_flag_over_env_over_file(capsys, monkeypatch):
    mycloud(capsys, "config", "set", "project", "from-file")
    assert mycloud(capsys, "config", "get", "project")[1] == "from-file\n"

    monkeypatch.setenv("MYCLOUD_CORE_PROJECT", "from-env")
    assert mycloud(capsys, "config", "get", "project")[1] == "from-env\n"

    mycloud(capsys, "storage", "buckets", "create", "b1", "--project", "from-flag", "-q")
    _, out, _ = mycloud(capsys, "storage", "buckets", "list", "--project=from-flag")
    assert "b1" in out


def test_unknown_property_is_rejected(capsys):
    code, _, err = mycloud(capsys, "config", "set", "core/colour", "red")
    assert code == 2
    assert "Unknown property [core/colour]" in err


def test_create_list_describe_delete(capsys, configured):
    code, out, err = mycloud(capsys, "compute", "instances", "create", "web-1", "--labels=env=dev")
    assert code == 0
    assert "Created [" in err  # status goes to stderr...
    assert out.splitlines()[0].split() == [
        "NAME",
        "ZONE",
        "MACHINE_TYPE",
        "STATUS",
    ]  # ...data to stdout

    _, out, _ = mycloud(capsys, "compute", "instances", "describe", "web-1", "--format=json")
    assert json.loads(out)["labels"] == {"env": "dev"}

    code, _, err = mycloud(capsys, "compute", "instances", "delete", "web-1", "--quiet")
    assert code == 0
    assert "Deleted [" in err

    code, _, err = mycloud(capsys, "compute", "instances", "describe", "web-1")
    assert code == 1
    assert "was not found" in err


def test_duplicate_create_fails(capsys, configured):
    mycloud(capsys, "compute", "instances", "create", "web-1")
    code, _, err = mycloud(capsys, "compute", "instances", "create", "web-1")
    assert code == 1
    assert "already exists" in err


def test_global_flags_work_anywhere(capsys, configured):
    mycloud(capsys, "compute", "instances", "create", "web-1")
    before = mycloud(capsys, "--format=value(name)", "compute", "instances", "list")
    middle = mycloud(capsys, "compute", "--format=value(name)", "instances", "list")
    after = mycloud(capsys, "compute", "instances", "list", "--format=value(name)")
    assert before == middle == after == (0, "web-1\n", "")


def test_delete_without_terminal_requires_quiet(capsys, configured, monkeypatch):
    mycloud(capsys, "compute", "instances", "create", "web-1")
    monkeypatch.setattr("sys.stdin.isatty", lambda: False, raising=False)
    code, _, err = mycloud(capsys, "compute", "instances", "delete", "web-1")
    assert code == 1
    assert "--quiet" in err
    assert mycloud(capsys, "compute", "instances", "describe", "web-1")[0] == 0


def test_filter_sort_limit(capsys, configured):
    mycloud(capsys, "compute", "instances", "create", "web-1", "web-2", "db-1")
    mycloud(capsys, "compute", "instances", "stop", "web-2")

    _, out, _ = mycloud(
        capsys, "compute", "instances", "list", "--filter=name~^web", "--format=value(name,status)"
    )
    assert out == "web-1\tRUNNING\nweb-2\tTERMINATED\n"

    _, out, _ = mycloud(
        capsys,
        "compute",
        "instances",
        "list",
        "--sort-by=~name",
        "--limit=1",
        "--format=value(name)",
    )
    assert out == "web-2\n"


def test_empty_list_reports_on_stderr(capsys, configured):
    code, out, err = mycloud(capsys, "storage", "buckets", "list")
    assert (code, out) == (0, "")
    assert "Listed 0 items." in err


def test_invalid_name_is_a_usage_error(capsys, configured):
    code, _, err = mycloud(capsys, "compute", "instances", "create", "Web_1")
    assert code == 2
    assert "invalid name" in err


def test_invalid_format(capsys, configured):
    code, _, err = mycloud(capsys, "compute", "zones", "list", "--format=xml")
    assert code == 2
    assert "Invalid format [xml]" in err
