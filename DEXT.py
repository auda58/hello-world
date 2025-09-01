import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
import platform
import tkinter.font as tkfont
try:
    # For a modern look and feel. Install with: pip install ttkthemes
    from ttkthemes import ThemedTk
except ImportError:
    ThemedTk = tk.Tk  # Fallback to standard Tk if ttkthemes is not installed

# --- Configuration ---
ARXML_OUTPUT_FILE = 'dext_output.arxml'
AUTOSAR_NAMESPACE = "http://autosar.org/schema/r4.0"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = "http://autosar.org/schema/r4.0 AUTOSAR_00053.xsd"


class DIDEditorWindow(tk.Toplevel):
    """A Toplevel window for adding or editing a single DID and its signals."""

    def __init__(self, parent, scale_factor=1.0, did_data=None, did_name=""):
        super().__init__(parent)
        self.parent = parent
        self.scale_factor = scale_factor
        self.did_data = did_data if did_data else {}
        self.original_did_name = did_name
        self.AUTOSAR_TYPES = [
            'uint8', 'uint16', 'uint32', 'uint64', 'sint8', 'sint16', 'sint32',
            'sint64', 'boolean', 'float32', 'float64', 'string'
        ]

        self.title("DID Editor")
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        if did_data:
            self._populate_data()

    def _create_widgets(self):
        scaled_pad = int(10 * self.scale_factor)
        scaled_pad_small = int(5 * self.scale_factor)
        scaled_pady_micro = max(1, int(2 * self.scale_factor))

        main_frame = ttk.Frame(self, padding=scaled_pad)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- DID Properties ---
        did_props_frame = ttk.LabelFrame(main_frame,
                                         text="DID Properties",
                                         padding=scaled_pad)
        did_props_frame.pack(fill=tk.X, pady=(0, scaled_pad_small))

        ttk.Label(did_props_frame, text="DID Name:").grid(row=0,
                                                        column=0,
                                                        sticky="w",
                                                        padx=scaled_pad_small,
                                                        pady=scaled_pady_micro)
        self.name_var = tk.StringVar()
        ttk.Entry(did_props_frame, textvariable=self.name_var).grid(row=0,
                                                                  column=1,
                                                                  sticky="ew",
                                                                  padx=scaled_pad_small,
                                                                  pady=scaled_pady_micro)

        ttk.Label(did_props_frame, text="DID ID (Hex):").grid(row=1,
                                                            column=0,
                                                            sticky="w",
                                                            padx=scaled_pad_small,
                                                            pady=scaled_pady_micro)
        self.id_var = tk.StringVar()
        ttk.Entry(did_props_frame, textvariable=self.id_var).grid(row=1,
                                                                column=1,
                                                                sticky="ew",
                                                                padx=scaled_pad_small,
                                                                pady=scaled_pady_micro)
        did_props_frame.columnconfigure(1, weight=1)

        # --- Access Rights ---
        access_frame = ttk.LabelFrame(main_frame,
                                      text="Access Rights",
                                      padding=scaled_pad)
        access_frame.pack(fill=tk.X, pady=scaled_pad_small)
        access_frame.columnconfigure(1, weight=1)

        # Read Access
        self.read_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            access_frame,
            text="Enable Read Access",
            variable=self.read_enabled_var,
            command=self._toggle_read_controls).grid(row=0,
                                                      column=0,
                                                      columnspan=2,
                                                      sticky="w")

        ttk.Label(access_frame, text="Read Session:").grid(row=1,
                                                           column=0,
                                                           sticky="w",
                                                            padx=scaled_pad_small,
                                                            pady=scaled_pady_micro)
        self.session_var = tk.StringVar()
        self.read_session_combo = ttk.Combobox(
            access_frame,
            textvariable=self.session_var,
            values=["Default Session", "Extended Session", "Programming Session"])
        self.read_session_combo.grid(row=1, column=1, sticky="ew", padx=scaled_pad_small, pady=scaled_pady_micro)

        ttk.Label(access_frame, text="Read Security:").grid(row=2,
                                                             column=0,
                                                             sticky="w",
                                                             padx=scaled_pad_small,
                                                             pady=scaled_pady_micro)
        self.security_var = tk.StringVar()
        self.read_security_combo = ttk.Combobox(
            access_frame,
            textvariable=self.security_var,
            values=["No Security", "Level 1", "Level 2"])
        self.read_security_combo.grid(row=2,
                                       column=1,
                                       sticky="ew",
                                       padx=scaled_pad_small,
                                       pady=scaled_pady_micro)

        # Separator
        ttk.Separator(access_frame, orient='horizontal').grid(row=3,
                                                               column=0,
                                                               columnspan=2,
                                                               sticky='ew',
                                                               pady=scaled_pad)

        # Write Access
        self.write_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            access_frame,
            text="Enable Write Access",
            variable=self.write_enabled_var,
            command=self._toggle_write_controls).grid(row=4,
                                                      column=0,
                                                      columnspan=2,
                                                      sticky="w")

        ttk.Label(access_frame, text="Write Session:").grid(row=5,
                                                            column=0,
                                                            sticky="w",
                                                            padx=scaled_pad_small,
                                                            pady=scaled_pady_micro)
        self.write_session_var = tk.StringVar()
        self.write_session_combo = ttk.Combobox(
            access_frame,
            textvariable=self.write_session_var,
            values=["Default Session", "Extended Session", "Programming Session"])
        self.write_session_combo.grid(row=5, column=1, sticky="ew", padx=scaled_pad_small, pady=scaled_pady_micro)

        ttk.Label(access_frame, text="Write Security:").grid(row=6,
                                                             column=0,
                                                             sticky="w",
                                                             padx=scaled_pad_small,
                                                             pady=scaled_pady_micro)
        self.write_security_var = tk.StringVar()
        self.write_security_combo = ttk.Combobox(
            access_frame,
            textvariable=self.write_security_var,
            values=["No Security", "Level 1", "Level 2"])
        self.write_security_combo.grid(row=6, column=1, sticky="ew", padx=scaled_pad_small, pady=scaled_pady_micro)

        # --- Signals Management ---
        signals_frame = ttk.LabelFrame(main_frame,
                                       text="Signals",
                                       padding=scaled_pad)
        signals_frame.pack(fill=tk.BOTH, expand=True, pady=scaled_pad)

        self.signal_columns = ('SignalName', 'DataType', 'Size')
        self.signal_tree = ttk.Treeview(signals_frame,
                                        columns=self.signal_columns,
                                        show='headings')
        for col in self.signal_columns:
            self.signal_tree.heading(col, text=col)
            self.signal_tree.column(col, width=int(100 * self.scale_factor))
        self.signal_tree.pack(fill=tk.BOTH, expand=True)
        self.signal_tree.bind("<Double-1>", self.on_double_click_signal)

        signal_btn_frame = ttk.Frame(signals_frame)
        signal_btn_frame.pack(fill=tk.X, pady=scaled_pad_small)
        ttk.Button(signal_btn_frame,
                   text="Add Signal",
                   command=self.add_signal).pack(side=tk.LEFT, padx=(0, scaled_pad_small))
        ttk.Button(signal_btn_frame,
                   text="Delete Signal",
                   command=self.delete_signal).pack(side=tk.LEFT, padx=scaled_pad_small)

        # --- Save/Cancel Buttons ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=scaled_pad_small)
        ttk.Button(action_frame,
                   text="Save & Close",
                   command=self.save_and_close,
                   style='Accent.TButton').pack(side=tk.RIGHT)
        ttk.Button(action_frame, text="Cancel",
                   command=self.destroy).pack(side=tk.RIGHT, padx=scaled_pad_small)

        self._toggle_read_controls()
        self._toggle_write_controls()

    def _populate_data(self):
        """Fills the editor fields with existing DID data."""
        self.name_var.set(self.original_did_name)
        self.id_var.set(self.did_data.get("id", ""))
        self.read_enabled_var.set(self.did_data.get("read_enabled", True))
        self.session_var.set(self.did_data.get("session", "Default Session"))
        self.security_var.set(self.did_data.get("security", "No Security"))
        self.write_enabled_var.set(self.did_data.get("write_enabled", False))
        self.write_session_var.set(
            self.did_data.get("write_session", "Extended Session"))
        self.write_security_var.set(
            self.did_data.get("write_security", "Level 1"))

        for signal in self.did_data.get("signals", []):
            self.signal_tree.insert(
                '',
                tk.END,
                values=[signal['name'], signal['type'], signal['size']])

        self._toggle_read_controls()
        self._toggle_write_controls()

    def _toggle_read_controls(self):
        """Enable or disable read access controls based on the checkbox state."""
        state = tk.NORMAL if self.read_enabled_var.get() else tk.DISABLED
        self.read_session_combo.config(state=state)
        self.read_security_combo.config(state=state)

    def _toggle_write_controls(self):
        """Enable or disable write access controls based on the checkbox state."""
        state = tk.NORMAL if self.write_enabled_var.get() else tk.DISABLED
        self.write_session_combo.config(state=state)
        self.write_security_combo.config(state=state)

    def add_signal(self):
        self.signal_tree.insert('', tk.END, values=['NewSignal', 'uint8', '1'])

    def delete_signal(self):
        selected = self.signal_tree.selection()
        if selected:
            self.signal_tree.delete(selected[0])

    def on_double_click_signal(self, event):
        region = self.signal_tree.identify("region", event.x, event.y)
        if region != "cell": return

        column_id = self.signal_tree.identify_column(event.x)
        column_idx = int(column_id.replace('#', '')) - 1
        selected_iid = self.signal_tree.focus()
        if not selected_iid: return

        x, y, width, height = self.signal_tree.bbox(selected_iid, column_id)

        current_value = self.signal_tree.item(selected_iid, 'values')[column_idx]
        editor_var = tk.StringVar(value=current_value)

        column_name = self.signal_columns[column_idx]
        if column_name == 'DataType':
            editor = ttk.Combobox(self.signal_tree,
                                  textvariable=editor_var,
                                  values=self.AUTOSAR_TYPES)
        else:
            editor = ttk.Entry(self.signal_tree, textvariable=editor_var)

        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()

        def save_edit(event):
            """Saves the new value and destroys the editor widget."""
            new_values = list(self.signal_tree.item(selected_iid, 'values'))
            new_values[column_idx] = editor_var.get()
            self.signal_tree.item(selected_iid, values=new_values)
            editor.destroy()

        editor.bind("<Return>", save_edit)
        editor.bind("<FocusOut>", save_edit)
        if isinstance(editor, ttk.Combobox):
            editor.bind("<<ComboboxSelected>>", save_edit)

    def save_and_close(self):
        """Validates input and passes the data back to the main application."""
        new_did_name = self.name_var.get().strip()
        did_id = self.id_var.get().strip()
        if not new_did_name or not did_id:
            messagebox.showerror("Error",
                                 "DID Name and DID ID cannot be empty.",
                                 parent=self)
            return

        # Check if DID name is being changed to one that already exists
        if new_did_name != self.original_did_name and new_did_name in self.parent.dids_data:
            messagebox.showerror("Error",
                                 f"DID Name '{new_did_name}' already exists.",
                                 parent=self)
            return

        if not self.read_enabled_var.get() and not self.write_enabled_var.get():
            if not messagebox.askyesno(
                    "Warning",
                    "Neither Read nor Write access is enabled. The DID will be defined but not accessible. Continue?",
                    parent=self):
                return

        signals = []
        for child_id in self.signal_tree.get_children():
            values = self.signal_tree.item(child_id, 'values')
            signals.append({
                "name": values[0],
                "type": values[1],
                "size": values[2]
            })

        updated_did = {
            "id": did_id,
            "read_enabled": self.read_enabled_var.get(),
            "session": self.session_var.get(),
            "security": self.security_var.get(),
            "write_enabled": self.write_enabled_var.get(),
            "write_session": self.write_session_var.get(),
            "write_security": self.write_security_var.get(),
            "signals": signals
        }

        self.parent.update_did(self.original_did_name, new_did_name,
                               updated_did)
        self.destroy()


class DextGeneratorApp(ThemedTk):
    """Main GUI application for the DEXT Generator."""

    TYPE_SIZE_MAP = {
        'uint8': 1, 'sint8': 1, 'boolean': 1,
        'uint16': 2, 'sint16': 2,
        'uint32': 4, 'sint32': 4, 'float32': 4,
        'uint64': 8, 'sint64': 8, 'float64': 8,
    }

    def __init__(self):
        super().__init__()
        # Set a modern theme. Fallback is handled in the import statement.
        if ThemedTk != tk.Tk:
            self.set_theme("arc")

        # --- DPI Scaling ---
        self.scale_factor = self._get_dpi_scale()
        self._configure_styles()

        self.title("DEXT Generator Tool")
        self.dids_data = {}
        self._create_widgets()
        self._center_window()

    def _get_dpi_scale(self):
        """Calculates the UI scaling factor based on the system's DPI."""
        if platform.system() == "Windows":
            try:
                # The DPI awareness is set before this class is instantiated.
                # 96 DPI is the standard, so we get a scaling factor from that.
                from ctypes import windll
                return windll.user32.GetDpiForSystem() / 96.0
            except (ImportError, AttributeError):
                # This can happen on non-Windows systems or if ctypes fails.
                return 1.0
        return 1.0  # Default for other OS

    def _configure_styles(self):
        """Configures all custom ttk styles, applying DPI scaling."""
        style = ttk.Style(self)

        # Get base font information
        default_font = tkfont.nametofont("TkDefaultFont")
        font_family = default_font.cget("family")
        font_size = default_font.cget("size")

        # Apply scaling if necessary
        if self.scale_factor > 1.0:
            scaled_size = int(font_size * self.scale_factor)

            # Scale the three default fonts of Tkinter
            default_font.configure(size=scaled_size)
            tkfont.nametofont("TkTextFont").configure(size=scaled_size)
            tkfont.nametofont("TkFixedFont").configure(size=scaled_size)

            font_size = scaled_size  # Use the new scaled size for custom styles

        # Configure custom styles using the (potentially scaled) font size
        bold_font = (font_family, font_size, 'bold')

        style.configure("Treeview.Heading", font=bold_font)
        style.configure('Accent.TButton', font=bold_font)
        style.configure('Generate.TButton', font=bold_font,
                        background='lightgreen')

    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _create_widgets(self):
        scaled_pad = int(10 * self.scale_factor)
        scaled_pad_small = int(5 * self.scale_factor)

        main_frame = ttk.Frame(self, padding=scaled_pad)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(pady=scaled_pad, fill=tk.BOTH, expand=True)

        self.columns = (
            'DID_Name', 'DID_ID', 'Read_Access', 'Read_Session', 'Read_Security',
            'Write_Access', 'Write_Session', 'Write_Security', 'Signal_Count',
            'Total_Size_Bytes'
        )
        self.tree = ttk.Treeview(tree_frame,
                                 columns=self.columns,
                                 show='headings')

        self.tree.heading('DID_Name', text='DID Name')
        self.tree.column('DID_Name', width=int(120 * self.scale_factor), anchor='w')
        self.tree.heading('DID_ID', text='DID ID')
        self.tree.column('DID_ID', width=int(60 * self.scale_factor), anchor='center')
        self.tree.heading('Read_Access', text='Read')
        self.tree.column('Read_Access', width=int(50 * self.scale_factor), anchor='center')
        self.tree.heading('Read_Session', text='Read Session')
        self.tree.column('Read_Session', width=int(120 * self.scale_factor), anchor='w')
        self.tree.heading('Read_Security', text='Read Security')
        self.tree.column('Read_Security', width=int(100 * self.scale_factor), anchor='w')
        self.tree.heading('Write_Access', text='Write')
        self.tree.column('Write_Access', width=int(50 * self.scale_factor), anchor='center')
        self.tree.heading('Write_Session', text='Write Session')
        self.tree.column('Write_Session', width=int(120 * self.scale_factor), anchor='w')
        self.tree.heading('Write_Security', text='Write Security')
        self.tree.column('Write_Security', width=int(100 * self.scale_factor), anchor='w')
        self.tree.heading('Signal_Count', text='Signals')
        self.tree.column('Signal_Count', width=int(60 * self.scale_factor), anchor='center')
        self.tree.heading('Total_Size_Bytes', text='Total Size (B)')
        self.tree.column('Total_Size_Bytes', width=int(90 * self.scale_factor), anchor='center')

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", lambda e: self.edit_did())

        # --- Action Buttons ---
        button_groups_frame = ttk.Frame(main_frame)
        button_groups_frame.pack(fill=tk.X, pady=scaled_pad_small)

        # File Operations Group
        file_ops_frame = ttk.LabelFrame(button_groups_frame, text="File Operations", padding=scaled_pad_small)
        file_ops_frame.pack(side=tk.LEFT, padx=(0, scaled_pad_small), fill=tk.X, expand=True)
        ttk.Button(file_ops_frame, text="Load from CSV", command=self.load_csv).pack(side=tk.LEFT, padx=scaled_pad_small, expand=True, fill=tk.X)
        ttk.Button(file_ops_frame, text="Save to CSV", command=self.save_csv).pack(side=tk.LEFT, padx=scaled_pad_small, expand=True, fill=tk.X)

        # DID Operations Group
        did_ops_frame = ttk.LabelFrame(button_groups_frame, text="DID Operations", padding=scaled_pad_small)
        did_ops_frame.pack(side=tk.LEFT, padx=(scaled_pad_small, 0), fill=tk.X, expand=True)
        ttk.Button(did_ops_frame, text="Add DID", command=self.add_did).pack(side=tk.LEFT, padx=scaled_pad_small, expand=True, fill=tk.X)
        ttk.Button(did_ops_frame, text="Edit Selected DID", command=self.edit_did).pack(side=tk.LEFT, padx=scaled_pad_small, expand=True, fill=tk.X)
        ttk.Button(did_ops_frame, text="Delete Selected DID", command=self.delete_did).pack(side=tk.LEFT, padx=scaled_pad_small, expand=True, fill=tk.X)

        # The 'Generate.TButton' style is now configured in the __init__ method
        ttk.Button(main_frame,
                   text="Generate DEXT File",
                   command=self.generate_dext,
                   style='Generate.TButton').pack(fill=tk.X, pady=scaled_pad)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self,
                  textvariable=self.status_var,
                  relief=tk.SUNKEN,
                  anchor='w',
                  padding=scaled_pad_small).pack(side=tk.BOTTOM, fill=tk.X)

    def _refresh_main_treeview(self):
        """Clears and repopulates the main DID list from the internal data structure."""
        for i in self.tree.get_children():
            self.tree.delete(i)

        for name, data in self.dids_data.items():
            signals = data.get("signals", [])
            signal_count = len(signals)

            total_size = 0
            try:
                for s in signals:
                    signal_type = s.get('type', '').lower()
                    if signal_type == 'string':
                        # For strings, size is specified in the 'size' field
                        total_size += int(s.get('size', 0))
                    else:
                        # For other types, use the predefined map
                        total_size += self.TYPE_SIZE_MAP.get(signal_type, 0)
            except (ValueError, TypeError):
                total_size = "N/A"

            # For backward compatibility, if read_enabled key doesn't exist, assume True
            is_read_enabled = data.get("read_enabled")
            if is_read_enabled is None:
                is_read_enabled = True  # Default for old data format
            read_enabled_str = "Yes" if is_read_enabled else "No"

            is_write_enabled = data.get("write_enabled", False)
            write_enabled_str = "Yes" if is_write_enabled else "No"

            values = [
                name,
                data.get('id', 'N/A'),
                read_enabled_str,
                data.get('session', 'N/A') if is_read_enabled else "---",
                data.get('security', 'N/A') if is_read_enabled else "---",
                write_enabled_str,
                data.get('write_session',
                         'N/A') if is_write_enabled else "---",
                data.get('write_security',
                         'N/A') if is_write_enabled else "---",
                signal_count,
                total_size
            ]
            self.tree.insert('', tk.END, values=values)

        self.status_var.set(f"Loaded {len(self.dids_data)} DIDs.")

    def load_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files",
                                                          "*.csv")])
        if not filepath: return

        temp_dids_data = defaultdict(lambda: {"signals": []})
        try:
            with open(filepath, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    did_name = row.get('DID_Name')
                    if not did_name: continue

                    did_info = temp_dids_data[did_name]

                    # Populate DID-level info only once from the first row for that DID
                    if 'id' not in did_info:
                        did_info['id'] = row.get('DID_ID')
                        # For backward compatibility, default Read_Enabled to True if not in CSV
                        did_info['read_enabled'] = row.get('Read_Enabled', 'True').lower() in ('true', '1', 'yes')
                        did_info['session'] = row.get('Session', 'Default Session')
                        did_info['security'] = row.get('SecurityLevel', 'No Security')
                        did_info['write_enabled'] = row.get('Write_Enabled', 'False').lower() in ('true', '1', 'yes')
                        did_info['write_session'] = row.get('Write_Session', 'Extended Session')
                        did_info['write_security'] = row.get('Write_Security', 'Level 1')

                    # Append signal info for every row that has a signal
                    if row.get('SignalName'):
                        did_info['signals'].append({
                            "name": row['SignalName'],
                            "type": row.get('DataType', 'uint8'),
                            "size": row.get('Size', '1')
                        })
            self.dids_data = dict(temp_dids_data)
            self._refresh_main_treeview()
        except Exception as e:
            messagebox.showerror("Error Loading CSV",
                                 f"An error occurred: {e}")

    def save_csv(self):
        """Saves the current list of DIDs and their signals to a CSV file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not filepath:
            return

        headers = [
            'DID_Name', 'DID_ID', 'Read_Enabled', 'Session', 'SecurityLevel',
            'Write_Enabled', 'Write_Session', 'Write_Security', 'SignalName',
            'DataType', 'Size'
        ]

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()

                for did_name, did_data in sorted(self.dids_data.items()):
                    read_enabled = did_data.get("read_enabled")
                    if read_enabled is None:
                        read_enabled = True  # Backward compatibility

                    base_row = {
                        'DID_Name': did_name,
                        'DID_ID': did_data.get('id', ''),
                        'Read_Enabled': read_enabled,
                        'Session': did_data.get('session', 'Default Session'),
                        'SecurityLevel': did_data.get('security', 'No Security'),
                        'Write_Enabled': did_data.get('write_enabled', False),
                        'Write_Session': did_data.get('write_session', 'Extended Session'),
                        'Write_Security': did_data.get('write_security', 'Level 1'),
                    }

                    signals = did_data.get('signals', [])
                    if not signals:
                        writer.writerow(base_row)
                    else:
                        for signal in signals:
                            row = base_row.copy()
                            row.update({
                                'SignalName': signal.get('name', ''),
                                'DataType': signal.get('type', ''),
                                'Size': signal.get('size', '')})
                            writer.writerow(row)
            self.status_var.set(f"Successfully saved DIDs to {filepath}")
        except Exception as e:
            messagebox.showerror("Error Saving CSV", f"An error occurred: {e}")

    def add_did(self):
        DIDEditorWindow(self, self.scale_factor)

    def edit_did(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection",
                                   "Please select a DID to edit.")
            return
        did_name = self.tree.item(selected[0], 'values')[0]
        DIDEditorWindow(self, self.scale_factor, self.dids_data.get(did_name), did_name)

    def delete_did(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection",
                                   "Please select a DID to delete.")
            return
        did_name = self.tree.item(selected[0], 'values')[0]
        if messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete '{did_name}'?"):
            del self.dids_data[did_name]
            self._refresh_main_treeview()

    def update_did(self, original_name, new_name, data):
        """Callback from the editor window to update the main data dictionary."""
        if original_name and original_name in self.dids_data and original_name != new_name:
            del self.dids_data[original_name]
        self.dids_data[new_name] = data
        self._refresh_main_treeview()

    def generate_dext(self):
        if not self.dids_data:
            messagebox.showerror("Error", "No DID data to generate.")
            return

        # --- Validation for unique DID IDs ---
        id_to_names = defaultdict(list)
        for did_name, data in self.dids_data.items():
            did_id = data.get('id', '').strip()
            if did_id:
                # Normalize to handle potential case differences e.g., 'F100' vs 'f100'
                id_to_names[did_id.lower()].append(did_name)

        duplicates = {
            id_val: names
            for id_val, names in id_to_names.items() if len(names) > 1
        }

        if duplicates:
            error_message = "Found duplicate DID IDs. Please correct them before generating:\n\n"
            for did_id_lower, did_names in duplicates.items():
                # Get the ID with its original casing from the first DID that uses it
                original_id_casing = self.dids_data[did_names[0]].get('id', did_id_lower)
                error_message += f"ID '{original_id_casing}' is used by DIDs: {', '.join(did_names)}\n"

            messagebox.showerror("Duplicate DID IDs", error_message)
            self.status_var.set("Generation failed: Duplicate DID IDs found.")
            return
        # --- End Validation ---

        self.status_var.set(
            f"Generating DEXT for {len(self.dids_data)} DIDs...")
        self._run_generation_logic(self.dids_data)

    # --- XML Generation Logic (largely the same, just adapted for new data structure) ---
    def _run_generation_logic(self, dids_data):
        ET.register_namespace('', AUTOSAR_NAMESPACE)
        root = ET.Element(
            "AUTOSAR", {f"{{{XSI_NAMESPACE}}}schemaLocation": SCHEMA_LOCATION})
        ar_packages = ET.SubElement(root, "AR-PACKAGES")

        dext_elements = self._create_ar_package(ar_packages,
                                                "MyECU_DiagnosticExtract")
        data_elements_package = self._create_ar_package(
            ar_packages, "MyECU_DataElements")
        data_types_package = self._create_ar_package(ar_packages,
                                                     "MyECU_DataTypes")
        access_perms_package = self._create_ar_package(
            ar_packages, "MyECU_AccessPermissions")

        # Create common access control objects
        ET.SubElement(access_perms_package, "DIAGNOSTIC-SESSION-CONTROL").set(
            "SHORT-NAME", "Default_Session")
        ET.SubElement(access_perms_package, "DIAGNOSTIC-SESSION-CONTROL").set(
            "SHORT-NAME", "Extended_Session")
        ET.SubElement(access_perms_package, "DIAGNOSTIC-SESSION-CONTROL").set(
            "SHORT-NAME", "Programming_Session")
        ET.SubElement(access_perms_package,
                      "DIAGNOSTIC-SECURITY-LEVEL").set("SHORT-NAME",
                                                       "No_Security")
        ET.SubElement(access_perms_package,
                      "DIAGNOSTIC-SECURITY-LEVEL").set("SHORT-NAME", "Level_1")
        ET.SubElement(access_perms_package,
                      "DIAGNOSTIC-SECURITY-LEVEL").set("SHORT-NAME", "Level_2")

        for did_name, data in dids_data.items():
            did_dec = str(int(data['id'], 16))
            did_element = ET.SubElement(dext_elements,
                                        "DIAGNOSTIC-DATA-IDENTIFIER")
            ET.SubElement(did_element, "SHORT-NAME").text = did_name
            ET.SubElement(did_element, "ID").text = did_dec
            data_element_refs = ET.SubElement(did_element, "DATA-ELEMENT-REFS")

            for signal in data['signals']:
                signal_name = signal['name']
                # Make short-names unique by prepending DID name to avoid conflicts
                unique_element_name = f"{did_name}_{signal_name}"

                data_element = ET.SubElement(
                    data_elements_package, "DATA-ELEMENT-PROTOTYPE")
                ET.SubElement(data_element,
                              "SHORT-NAME").text = unique_element_name
                type_name = self._create_implementation_data_type(
                    data_types_package, signal, unique_element_name)
                ET.SubElement(data_element,
                              "TYPE-TREF",
                              DEST="IMPLEMENTATION-DATA-TYPE"
                              ).text = f"/MyECU_DataTypes/{type_name}"
                ET.SubElement(data_element_refs,
                              "DATA-ELEMENT-REF",
                              DEST="DATA-ELEMENT-PROTOTYPE"
                              ).text = f"/MyECU_DataElements/{unique_element_name}"

            # --- Create Read Access Permission ---
            if data.get("read_enabled", True):  # Default to True for backward compatibility
                session = data['session'].replace(" ", "_")
                security = data['security'].replace(" ", "_")

                read_access_perm = ET.SubElement(access_perms_package,
                                                 "DIAGNOSTIC-ACCESS-PERMISSION")
                ET.SubElement(read_access_perm,
                              "SHORT-NAME").text = f"{did_name}_Read_Access"
                ET.SubElement(
                    read_access_perm, "SERVICE-REF", DEST="DIAGNOSTIC-SERVICE-CLASS"
                ).text = "/AUTOSAR_Dcm/DiagnosticServices/ReadDataByIdentifier"
                ET.SubElement(ET.SubElement(read_access_perm,
                                            "DIAG-DATA-IDENTIFIER-REFS"),
                              "DIAG-DATA-IDENTIFIER-REF",
                              DEST="DIAGNOSTIC-DATA-IDENTIFIER"
                              ).text = f"/MyECU_DiagnosticExtract/{did_name}"
                ET.SubElement(ET.SubElement(read_access_perm, "SESSIONS"),
                              "SESSION-REF",
                              DEST="DIAGNOSTIC-SESSION-CONTROL"
                              ).text = f"/MyECU_AccessPermissions/{session}"
                ET.SubElement(ET.SubElement(read_access_perm, "SECURITY-LEVELS"),
                              "SECURITY-LEVEL-REF",
                              DEST="DIAGNOSTIC-SECURITY-LEVEL"
                              ).text = f"/MyECU_AccessPermissions/{security}"

            # --- Create Write Access Permission (if enabled) ---
            if data.get("write_enabled"):
                write_session = data.get("write_session", "Default Session").replace(" ", "_")
                write_security = data.get("write_security", "No Security").replace(" ", "_")

                write_access_perm = ET.SubElement(
                    access_perms_package, "DIAGNOSTIC-ACCESS-PERMISSION")
                ET.SubElement(
                    write_access_perm, "SHORT-NAME").text = f"{did_name}_Write_Access"
                ET.SubElement(write_access_perm, "SERVICE-REF",
                              DEST="DIAGNOSTIC-SERVICE-CLASS").text = "/AUTOSAR_Dcm/DiagnosticServices/WriteDataByIdentifier"
                ET.SubElement(ET.SubElement(write_access_perm, "DIAG-DATA-IDENTIFIER-REFS"),
                              "DIAG-DATA-IDENTIFIER-REF",
                              DEST="DIAGNOSTIC-DATA-IDENTIFIER").text = f"/MyECU_DiagnosticExtract/{did_name}"
                ET.SubElement(ET.SubElement(write_access_perm, "SESSIONS"),
                              "SESSION-REF",
                              DEST="DIAGNOSTIC-SESSION-CONTROL").text = f"/MyECU_AccessPermissions/{write_session}"
                ET.SubElement(ET.SubElement(write_access_perm, "SECURITY-LEVELS"),
                              "SECURITY-LEVEL-REF",
                              DEST="DIAGNOSTIC-SECURITY-LEVEL").text = f"/MyECU_AccessPermissions/{write_security}"

        try:
            xml_str = ET.tostring(root, 'utf-8')
            pretty_xml_str = minidom.parseString(xml_str).toprettyxml(
                indent="    ", encoding="utf-8")
            with open(ARXML_OUTPUT_FILE, 'wb') as f:
                f.write(pretty_xml_str)
            messagebox.showinfo(
                "Success",
                f"DEXT file '{ARXML_OUTPUT_FILE}' generated successfully.")
            self.status_var.set(
                f"Successfully generated '{ARXML_OUTPUT_FILE}'")
        except Exception as e:
            messagebox.showerror("Generation Error", f"An error occurred: {e}")

    def _create_ar_package(self, parent, short_name):
        ar_package = ET.SubElement(parent, "AR-PACKAGE")
        ET.SubElement(ar_package, "SHORT-NAME").text = short_name
        return ET.SubElement(ar_package, "ELEMENTS")

    def _create_implementation_data_type(self, parent, signal_info,
                                         unique_prefix):
        data_type = signal_info['type']
        size = signal_info['size']
        short_name = f"{unique_prefix}_Type"

        if data_type.lower() == 'string':
            impl_data_type = ET.SubElement(parent, "IMPLEMENTATION-DATA-TYPE")
            ET.SubElement(impl_data_type, "SHORT-NAME").text = short_name
            ET.SubElement(impl_data_type, "CATEGORY").text = "ARRAY"
            sub_elements = ET.SubElement(impl_data_type, "SUB-ELEMENTS")
            element = ET.SubElement(sub_elements,
                                    "IMPLEMENTATION-DATA-TYPE-ELEMENT")
            ET.SubElement(
                element, "SHORT-NAME").text = f"{unique_prefix}_Byte"
            ET.SubElement(element, "CATEGORY").text = "TYPE_REFERENCE"
            ET.SubElement(element, "ARRAY-SIZE").text = str(size)
            props = ET.SubElement(element, "SW-DATA-DEF-PROPS")
            variants = ET.SubElement(props, "SW-DATA-DEF-PROPS-VARIANTS")
            cond = ET.SubElement(variants, "SW-DATA-DEF-PROPS-CONDITIONAL")
            ET.SubElement(
                cond,
                "IMPLEMENTATION-DATA-TYPE-REF",
                DEST="IMPLEMENTATION-DATA-TYPE"
            ).text = "/AUTOSAR_Platform/ImplementationDataTypes/uint8"
        else:
            impl_data_type = ET.SubElement(parent, "IMPLEMENTATION-DATA-TYPE")
            ET.SubElement(impl_data_type, "SHORT-NAME").text = short_name
            ET.SubElement(impl_data_type, "CATEGORY").text = "VALUE"
            props = ET.SubElement(impl_data_type, "SW-DATA-DEF-PROPS")
            variants = ET.SubElement(props, "SW-DATA-DEF-PROPS-VARIANTS")
            cond = ET.SubElement(variants, "SW-DATA-DEF-PROPS-CONDITIONAL")
            ET.SubElement(
                cond, "BASE-TYPE-REF", DEST="IMPLEMENTATION-DATA-TYPE"
            ).text = f"/AUTOSAR_Platform/ImplementationDataTypes/{data_type}"

        return short_name


if __name__ == "__main__":
    try:
        # Make the application DPI-aware on Windows, resulting in a sharper UI.
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError):
        pass  # This will fail on non-Windows systems, which is fine.
    app = DextGeneratorApp()
    app.mainloop()
