;;; bookstack-editor.el --- bookstack wiki emacs integration  -*- lexical-binding: t; -*-

;; This file is NOT part of GNU Emacs.

;; bookstack-editor.el is free software: you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation, either version 3 of the License, or
;; (at your option) any later version.

;; bookstack-editor.el is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with bookstack-editor.el.
;; If not, see <https://www.gnu.org/licenses/>.

;;; Commentary:

;; This file contains the OpenAI API related functions for org-ai.

;;; Code:

(defun bookstack-compilation-buffer-name (&optional major-mode)
  (concat "*bookstack-editor*"))

(defun bookstack-sync (&optional force)
  "Run bookstack-editor sync."
  (interactive "P")
  (message "Syncing bookstack (force=%s)" force)
  (save-window-excursion
    (compile (concat "bookstack-editor sync" (if force " --force" "")))))

(defun bookstack-after-save-hook ()
  (when (and (eq major-mode 'markdown-mode)
             (bound-and-true-p bookstack-mode))
    (bookstack-sync)))

(define-minor-mode bookstack-mode
  "Minor mode for bookstack-editor."
  :lighter " Bookstack"
  :keymap (let ((map (make-sparse-keymap)))
            (define-key map (kbd "C-c C-s") 'bookstack-sync)
            map))

(provide 'bookstack-editor)

;;; bookstack-editor.el ends here
