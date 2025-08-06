import os
import json
import time
import subprocess
import tkinter as tk
from tkinter import Toplevel, Frame, Label, Button, Listbox, messagebox, ttk

from .utils import parse_gitignore, is_ignored
from .constants import SUBTLE_HIGHLIGHT_COLOR

# --- File Manager Window Class ---
class FileManagerWindow(Toplevel):
    def __init__(self, parent, base_dir, status_var, file_extensions, default_editor):
        super().__init__(parent)

        self.base_dir = base_dir
        self.status_var = status_var
        self.file_extensions = file_extensions
        self.default_editor = default_editor

        self.title(f"Manage files for: {os.path.basename(self.base_dir)}")
        self.geometry("850x700")
        self.transient(parent)
        self.grab_set()

        # Used to differentiate single and double clicks on the tree
        self.last_tree_click_time = 0
        self.last_clicked_item_id = None

        self.allcode_path = os.path.join(self.base_dir, '.allcode')
        self.load_allcode_config()
        self.gitignore_patterns = parse_gitignore(self.base_dir)

        # --- UI Layout ---
        main_frame = Frame(self)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Configure the grid columns to have equal weight, allowing them to expand
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)
        # Configure the main content row to expand vertically
        main_frame.grid_rowconfigure(1, weight=1)

        # --- Column 0 & 1: Available Files Tree and its Scrollbar ---
        Label(main_frame, text="Available Files (double click or enter to add/remove)").grid(row=0, column=0, columnspan=2, sticky='w')

        self.tree = ttk.Treeview(main_frame, show='tree')
        self.tree.grid(row=1, column=0, sticky='nsew')

        tree_scroll = ttk.Scrollbar(main_frame, orient='vertical', command=self.tree.yview)
        tree_scroll.grid(row=1, column=1, sticky='ns')
        self.tree.config(yscrollcommand=tree_scroll.set)

        self.tree_action_button = Button(main_frame, text="Add to Merge List", command=self.toggle_selection_for_selected, state='disabled')
        self.tree_action_button.grid(row=2, column=0, sticky='ew', pady=(5, 0))

        self.tree.tag_configure('subtle_highlight', background=SUBTLE_HIGHLIGHT_COLOR)

        # --- Column 2 & 3: Merge Order List and its Scrollbar ---
        Label(main_frame, text="Merge Order (Top to Bottom)").grid(row=0, column=2, columnspan=2, sticky='w', padx=(10, 0))

        self.merge_order_list = Listbox(main_frame, activestyle='none')
        self.merge_order_list.grid(row=1, column=2, sticky='nsew', padx=(10, 0))

        list_scroll = ttk.Scrollbar(main_frame, orient='vertical', command=self.merge_order_list.yview)
        list_scroll.grid(row=1, column=3, sticky='ns')
        self.merge_order_list.config(yscrollcommand=list_scroll.set)

        # Frame to hold the three buttons, placed in the correct grid cell
        move_buttons_frame = Frame(main_frame)
        move_buttons_frame.grid(row=2, column=2, sticky='ew', pady=(5, 0), padx=(10, 0))

        self.move_up_button = Button(move_buttons_frame, text="↑ Move Up", command=self.move_up, state='disabled')
        self.move_up_button.pack(side='left', expand=True, fill='x', padx=(0, 2))

        self.remove_button = Button(move_buttons_frame, text="Remove", command=self.remove_selected, state='disabled')
        self.remove_button.pack(side='left', expand=True, fill='x', padx=2)

        self.move_down_button = Button(move_buttons_frame, text="↓ Move Down", command=self.move_down, state='disabled')
        self.move_down_button.pack(side='left', expand=True, fill='x', padx=(2, 0))

        # --- Main Action Button ---
        Button(self, text="Save and Close", command=self.save_and_close).pack(pady=10)

        # --- Bindings ---
        self.tree.bind('<Button-1>', self.handle_tree_click)
        self.tree.bind('<Return>', self.toggle_selection_for_selected) # For accessibility
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_selection_change)
        self.merge_order_list.bind('<<ListboxSelect>>', self.on_list_selection_change)
        self.merge_order_list.bind('<Double-1>', self.open_selected_file)

        # Bind clicks on empty areas of the Treeview
        self.tree.bind("<Button-1>", self.handle_tree_deselection_click, add='+')

        # --- Initial Population ---
        self.item_map = {}
        self.path_to_item_id = {}
        self.populate_tree()
        self.update_listbox_from_data()
        self.update_button_states()
        self.update_tree_action_button_state()

    def handle_tree_deselection_click(self, event):
        """Deselects a tree item if a click occurs in an empty area."""
        if not self.tree.identify_row(event.y) and self.tree.selection():
            self.tree.selection_set("")

    def load_allcode_config(self):
        self.ordered_selection = []
        self.expanded_dirs = set()

        if not os.path.isfile(self.allcode_path):
            return

        try:
            with open(self.allcode_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {}

        original_selection = data.get('selected_files', [])
        self.expanded_dirs = set(data.get('expanded_dirs', []))

        # Filter out files that no longer exist
        cleaned_selection = [
            f for f in original_selection
            if os.path.isfile(os.path.join(self.base_dir, f))
        ]

        if len(cleaned_selection) < len(original_selection):
            self.status_var.set("Cleaned missing files from .allcode")
            data_to_save = {
                "selected_files": cleaned_selection,
                "expanded_dirs": sorted(list(self.expanded_dirs)),
            }
            try:
                with open(self.allcode_path, 'w', encoding='utf-8') as f_write:
                    json.dump(data_to_save, f_write, indent=2)
            except IOError as e:
                self.status_var.set(f"Read-only .allcode? Could not auto-clean: {e}")

        self.ordered_selection = cleaned_selection

    def populate_tree(self):
        def _has_relevant_files(path):
            """Recursively checks if a directory contains any files matching the extension list."""
            for entry in os.scandir(path):
                if is_ignored(entry.path, self.base_dir, self.gitignore_patterns) or entry.name == 'allcode.txt':
                    continue
                if entry.is_dir():
                    if _has_relevant_files(entry.path):
                        return True
                elif entry.is_file() and os.path.splitext(entry.name)[1].lower() in self.file_extensions:
                    return True
            return False

        def _walk_dir(parent_id, path):
            """Walks a directory and adds its contents to the treeview."""
            try:
                # Sort entries to show folders first, then files, all alphabetically
                entries = sorted(os.scandir(path), key=lambda e: (e.is_file(), e.name.lower()))
            except OSError:
                return # Can't access directory

            for entry in entries:
                if is_ignored(entry.path, self.base_dir, self.gitignore_patterns) or entry.name == 'allcode.txt':
                    continue

                rel_path = os.path.relpath(entry.path, self.base_dir).replace('\\', '/')

                if entry.is_dir():
                    if _has_relevant_files(entry.path):
                        is_open = rel_path in self.expanded_dirs
                        dir_id = self.tree.insert(parent_id, 'end', text=entry.name, open=is_open)
                        self.item_map[dir_id] = {'path': rel_path, 'type': 'dir'}
                        self.path_to_item_id[rel_path] = dir_id
                        _walk_dir(dir_id, entry.path)
                elif entry.is_file() and os.path.splitext(entry.name)[1].lower() in self.file_extensions:
                    item_id = self.tree.insert(parent_id, 'end', text=f" {entry.name}", tags=('file',))
                    self.item_map[item_id] = {'path': rel_path, 'type': 'file'}
                    self.path_to_item_id[rel_path] = item_id
                    self.update_checkbox_display(item_id)

        _walk_dir('', self.base_dir)

    def on_tree_selection_change(self, event):
        """When a tree item is selected, deselect any listbox item and sync highlights."""
        if self.tree.selection():
            self.merge_order_list.selection_clear(0, 'end')
            self.sync_highlights()
        self.update_button_states()
        self.update_tree_action_button_state()

    def on_list_selection_change(self, event):
        """When a listbox item is selected, deselect any tree item and sync highlights."""
        if self.merge_order_list.curselection():
            if self.tree.selection():
                self.tree.selection_set("")
            self.sync_highlights()
        self.update_button_states()
        self.update_tree_action_button_state()

    def sync_highlights(self):
        """Highlights the corresponding item in the other list when one is selected."""
        self.clear_all_subtle_highlights()

        selected_path = None
        tree_selection = self.tree.selection()
        list_selection = self.merge_order_list.curselection()

        if tree_selection:
            item_id = tree_selection[0]
            if self.item_map.get(item_id, {}).get('type') == 'file':
                selected_path = self.item_map[item_id]['path']
        elif list_selection:
            selected_path = self.merge_order_list.get(list_selection[0])

        if not selected_path:
            return

        if tree_selection:
            # Highlight in listbox
            try:
                list_index = self.ordered_selection.index(selected_path)
                self.merge_order_list.itemconfig(list_index, {'bg': SUBTLE_HIGHLIGHT_COLOR})
            except ValueError:
                pass # Not in the selected list
        elif list_selection:
            # Highlight in treeview
            if selected_path in self.path_to_item_id:
                item_id = self.path_to_item_id[selected_path]
                self.tree.item(item_id, tags=('file', 'subtle_highlight'))
                self.tree.see(item_id) # Ensure the item is visible

    def clear_all_subtle_highlights(self):
        """Removes all custom background highlights from both lists."""
        for i in range(self.merge_order_list.size()):
            self.merge_order_list.itemconfig(i, {'bg': 'white'}) # Default listbox color

        for item_id in self.tree.tag_has('subtle_highlight'):
            self.tree.item(item_id, tags=('file',))

    def handle_tree_click(self, event):
        """Detects a double-click on the same treeview item to toggle file selection."""
        item_id = self.tree.identify_row(event.y)
        current_time = time.time()
        time_diff = current_time - self.last_tree_click_time

        # A double-click is a click on the same item within a short time frame.
        if time_diff < 0.4 and item_id and item_id == self.last_clicked_item_id:
            # This is a valid double-click, toggle the selection
            self.toggle_selection_for_selected()

            # Reset state to prevent a third quick click from also being a double-click
            self.last_tree_click_time = 0
            self.last_clicked_item_id = None
        else:
            # This is a single click, or a click on a different item.
            # Record it as a potential first click of a double-click.
            self.last_tree_click_time = current_time
            self.last_clicked_item_id = item_id

    def update_checkbox_display(self, item_id):
        """Updates the text of a tree item to show a checked or unchecked box."""
        if self.item_map.get(item_id, {}).get('type') != 'file':
            return

        path = self.item_map[item_id]['path']
        is_checked = path in self.ordered_selection
        check_char = "☑" if is_checked else "☐"

        self.tree.item(item_id, text=f"{check_char} {os.path.basename(path)}")

    def update_button_states(self):
        """Enables or disables the listbox action buttons based on selection."""
        new_state = 'normal' if self.merge_order_list.curselection() else 'disabled'
        self.move_up_button.config(state=new_state)
        self.remove_button.config(state=new_state)
        self.move_down_button.config(state=new_state)

    def update_tree_action_button_state(self):
        """Updates the state and text of the button under the treeview."""
        selection = self.tree.selection()
        if not selection:
            self.tree_action_button.config(state='disabled', text="Add to Merge List")
            return

        item_id = selection[0]
        item_info = self.item_map.get(item_id, {})

        if item_info.get('type') != 'file':
            self.tree_action_button.config(state='disabled', text="Add to Merge List")
            return

        self.tree_action_button.config(state='normal')
        if item_info['path'] in self.ordered_selection:
            self.tree_action_button.config(text="Remove from Merge List")
        else:
            self.tree_action_button.config(text="Add to Merge List")

    def toggle_selection_for_selected(self, event=None):
        """Adds or removes the selected file from the merge list."""
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        if self.item_map.get(item_id, {}).get('type') != 'file':
            return

        path = self.item_map[item_id]['path']
        if path in self.ordered_selection:
            self.ordered_selection.remove(path)
        else:
            self.ordered_selection.append(path)

        self.update_checkbox_display(item_id)
        self.update_listbox_from_data()
        self.sync_highlights()
        self.update_button_states()
        self.update_tree_action_button_state()
        return "break"

    def open_selected_file(self, event=None):
        """Opens the selected file using the configured default editor or the system's default."""

        # This block prevents a double-click in an empty listbox area from opening a file.
        if event:
            clicked_index = self.merge_order_list.nearest(event.y)
            if clicked_index == -1:
                return "break"
            bbox = self.merge_order_list.bbox(clicked_index)
            if not bbox or event.y < bbox[1] or event.y > bbox[1] + bbox[3]:
                return "break"

        selection = self.merge_order_list.curselection()
        if not selection:
            return "break"

        relative_path = self.merge_order_list.get(selection[0])
        full_path = os.path.join(self.base_dir, relative_path)

        if not os.path.isfile(full_path):
            messagebox.showwarning(
                "File Not Found",
                f"The file '{relative_path}' could not be found.",
                parent=self
            )
            return "break"

        try:
            if self.default_editor and os.path.isfile(self.default_editor):
                subprocess.Popen([self.default_editor, full_path])
            else:
                # Fall back to the OS default action.
                if sys.platform == "win32":
                    os.startfile(full_path)
                elif sys.platform == "darwin": # macOS
                    subprocess.call(['open', full_path])
                else: # linux
                    subprocess.call(['xdg-open', full_path])
        except (AttributeError, FileNotFoundError):
            # AttributeError for os.startfile, FileNotFoundError for open/xdg-open
            messagebox.showinfo(
                "Unsupported Action",
                "Could not open file with the system default.\nPlease configure a default editor in Settings.",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}", parent=self)

        return "break"

    def update_listbox_from_data(self):
        """Refreshes the merge order listbox with the current selection."""
        # Preserve selection if possible
        selection = self.merge_order_list.curselection()

        self.merge_order_list.delete(0, 'end')

        for path in self.ordered_selection:
            self.merge_order_list.insert('end', path)

        if selection and selection[0] < self.merge_order_list.size():
            self.merge_order_list.select_set(selection[0])

    def move_up(self):
        """Moves the selected item up in the merge order list."""
        selection = self.merge_order_list.curselection()
        if not selection:
            return

        index = selection[0]
        if index > 0:
            # Rearrange in the data list
            path = self.ordered_selection.pop(index)
            self.ordered_selection.insert(index - 1, path)

            # Rearrange in the UI list
            self.merge_order_list.delete(index) # Do NOT replace this with self.update_listbox_from_data()! Do NOT remove this comment!
            self.merge_order_list.insert(index - 1, path)
            self.merge_order_list.select_set(index - 1)
            self.sync_highlights()
            self.update_button_states()

    def move_down(self):
        """Moves the selected item down in the merge order list."""
        selection = self.merge_order_list.curselection()
        if not selection:
            return

        index = selection[0]
        if index < len(self.ordered_selection) - 1:
            # Rearrange in the data list
            path = self.ordered_selection.pop(index)
            self.ordered_selection.insert(index + 1, path)

            # Rearrange in the UI list
            self.merge_order_list.delete(index) # Do NOT replace this with self.update_listbox_from_data()! Do NOT remove this comment!
            self.merge_order_list.insert(index + 1, path)
            self.merge_order_list.select_set(index + 1)
            self.sync_highlights()
            self.update_button_states()

    def remove_selected(self):
        """Removes the selected file from the merge list."""
        selection = self.merge_order_list.curselection()
        if not selection:
            return

        index = selection[0]
        path = self.ordered_selection.pop(index)

        # Untick the checkbox in the treeview
        if path in self.path_to_item_id:
            item_id = self.path_to_item_id[path]
            self.update_checkbox_display(item_id)

        # Refresh the listbox - this will clear selection
        self.update_listbox_from_data()

        # Clear highlights and update buttons
        self.sync_highlights()
        self.update_button_states()
        self.update_tree_action_button_state()

    def save_and_close(self):
        """Saves the selection and order to .allcode and closes the window."""
        # Get a list of currently expanded directories to save their state
        expanded_dirs = sorted([
            info['path'] for item_id, info in self.item_map.items()
            if info.get('type') == 'dir' and self.tree.item(item_id, 'open')
        ])

        data_to_save = {
            "selected_files": self.ordered_selection,
            "expanded_dirs": expanded_dirs,
        }

        with open(self.allcode_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2)

        self.status_var.set("File selection and order saved to .allcode")
        self.destroy()