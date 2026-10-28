# Homebrew formula for mycloud.
#
# The repo doubles as its own tap, so users run:
#   brew tap kavisek/demo-cli-creation git@github.com:kavisek/demo-cli-creation.git
#   brew install mycloud
#
# The source is fetched with git over SSH, so anyone who can read the repo can
# install it with their normal GitHub SSH key, and nobody else can.
#
# Release checklist: bump mycloud/__init__.py, push tag vX.Y.Z, then update
# `tag` and `version` below to match and push.
class Mycloud < Formula
  desc "Small gcloud-style CLI for learning how to build command-line tools"
  homepage "https://github.com/kavisek/demo-cli-creation"
  url "git@github.com:kavisek/demo-cli-creation.git", using: :git, tag: "v0.1.0"
  version "0.1.0"
  license "MIT"
  head "git@github.com:kavisek/demo-cli-creation.git", using: :git, branch: "main"

  depends_on "uv" => :build
  depends_on "python@3.14"

  def install
    python = Formula["python@3.14"].opt_bin/"python3.14"
    system "uv", "build", "--wheel", "--out-dir", "dist"
    system python, "-m", "venv", libexec
    system libexec/"bin/pip", "install", "--no-deps", *Dir["dist/*.whl"]
    bin.install_symlink libexec/"bin/mycloud"
  end

  test do
    assert_match "mycloud #{version}", shell_output("#{bin}/mycloud version")
  end
end
