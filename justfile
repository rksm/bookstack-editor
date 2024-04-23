set dotenv-load

default:
    just --list

build:
  python -m build

run:
  python -m ./bookstack_editor.main
