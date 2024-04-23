# bookstack-editor

Programatically sync & edit [BookStack pages](https://www.bookstackapp.com/). Useful for editor integrations.

Setup:

### 1. Prepare a local wiki folder

In an empty folder (this will be the local wiki root directory) place a `.bookstack.json` file with the following content:

```json
{
  "url": "https://your-bookstack-url.com",
  "pages": {}
}
```

### 2. BookStack API Token

Create `.env` file with the following content:

```
BOOKSTACK_TOKEN_ID=YOUR_BOOKSTACK_TOKEN_ID
BOOKSTACK_TOKEN_SECRET=YOUR_BOOKSTACK
```

For creating an api token (as per [https://demo.bookstackapp.com/api/docs]()):

> Authentication to use the API is primarily done using API Tokens. Once the "Access System API" permission has been assigned to a user, a "API Tokens" section should be visible when editing their user profile. Choose "Create Token" and enter an appropriate name and expiry date, relevant for your API usage then press "Save". A "Token ID" and "Token Secret" will be immediately displayed. These values should be used as a header in API HTTP requests in the following format:

### 3. Optional: nix flake

Optional: For usage with nix. In your wiki root directory create a `flake.nix` file with the following content:
    
```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    bookstack-editor-pkg = {
      url = "github:rksm/bookstack-editor";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, bookstack-editor-pkg }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        bookstack-editor = bookstack-editor-pkg.packages.${system}.default;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [ bookstack-editor ];
        };
      }
    );
}
```

And create a `.envrc` file with the following content:

```sh
use flake

```

### 4. Usage

You can now sync the markdown pages of the wiki by running:

```sh
bookstack-editor sync
```

- Pages that exist remotely will be created in subfolders following a `book-slug/page-slug.md` naming scheme.
- Pages that exist locally but not remotely will be created if they are placed in a subfolder that corresponds to a book.
- Pages that are deleted remotely and have no local changes will be deleted locally. Otherwise they will be kept.
- Pages that are changed both locally and remotely will be skipped. You can run `bookstack-editor sync --force` to overwrite local changes with remote changes.

## Usage idea with emacs

I use this package with Emacs to automatically sync mardown files when I save them. A possible setup can look like this:

In your `init.el` or wherever you configure your Emacs:

```elisp
(use-package bookstack-editor
    :load-path (lambda () "path/to/bookstack-editor")
    :commands (bookstack-mode))
```

In directories that include wiki file, place `.dir-locals.el` file with the following content:

```elisp
((nil . ((eval . (progn
                   (bookstack-mode 1)
                   (add-hook 'after-save-hook 'bookstack-after-save-hook nil t))))))
```

You can then sync either by running `C-c C-s` or by saving a markdown file. If you prefer not to sync on save, leave the add-hook line out.
