import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict

# --- Configuration ---
ARXML_OUTPUT_FILE = 'dext_output.arxml'
AUTOSAR_NAMESPACE = "http://autosar.org/schema/r4.0"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = "http://autosar.org/schema/r4.0 AUTOSAR_4-3-0.xsd"

class DextGeneratorApp(tk.Tk):
    """A GUI application for generating AUTOSAR DEXT files from DID configurations."""

    def __init__(self):
        super().__init__()
        self.title("DEXT Generator Tool")
        self.geometry("950x600")
        
        self.dids_data = {}
        
        self._create_widgets()
        self._center_window()

    def _center_window(self):
        """Centers the main window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _create_widgets(self):
        """Creates and arranges all the widgets in the main window."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Treeview for DID Data ---
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.columns = ('DID', 'SignalName', 'DataType', 'Size', 'Session', 'SecurityLevel')
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show='headings')
        
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor='w')

        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side='right', fill='y')
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side='bottom', fill='x')
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self.on_double_click) # Bind double-click for editing

        # --- Buttons Frame ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="Load from CSV", command=self.load_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Add Row", command=self.add_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected Row", command=self.delete_row).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(main_frame, text="Generate DEXT File", command=self.generate_dext_from_gui, style='Accent.TButton').pack(fill=tk.X, pady=10)
        
        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor='w', padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Style for the main button
        style = ttk.Style(self)
        style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'))

    def on_double_click(self, event):
        """Handle double-click to edit a cell."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
            
        column_id = self.tree.identify_column(event.x)
        column_idx = int(column_id.replace('#', '')) - 1
        selected_iid = self.tree.focus()
        
        if not selected_iid:
            return

        x, y, width, height = self.tree.bbox(selected_iid, column_id)

        # Place an Entry widget over the cell
        entry_var = tk.StringVar(value=self.tree.item(selected_iid, 'values')[column_idx])
        entry = ttk.Entry(self, textvariable=entry_var)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()

        def save_edit(event):
            new_values = list(self.tree.item(selected_iid, 'values'))
            new_values[column_idx] = entry_var.get()
            self.tree.item(selected_iid, values=new_values)
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    def load_csv(self):
        """Opens a file dialog to load a CSV and populates the treeview."""
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        try:
            with open(filepath, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                # Clear existing data
                for i in self.tree.get_children():
                    self.tree.delete(i)
                # Insert new data
                for row in reader:
                    self.tree.insert('', tk.END, values=[row[col] for col in self.columns])
            self.status_var.set(f"Successfully loaded data from {filepath}")
        except Exception as e:
            messagebox.showerror("Error Loading CSV", f"An error occurred: {e}")
            self.status_var.set("Error loading CSV.")

    def add_row(self):
        """Adds a new, empty row to the treeview for manual entry."""
        self.tree.insert('', tk.END, values=['' for _ in self.columns])
        self.status_var.set("New row added. Double-click to edit.")

    def delete_row(self):
        """Deletes the currently selected row(s) from the treeview."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select one or more rows to delete.")
            return
        
        for item in selected_items:
            self.tree.delete(item)
        self.status_var.set(f"Deleted {len(selected_items)} row(s).")
    
    def generate_dext_from_gui(self):
        """Extracts data from the GUI and generates the DEXT ARXML file."""
        gui_data = []
        for child_id in self.tree.get_children():
            row_values = self.tree.item(child_id, 'values')
            row_dict = {self.columns[i]: row_values[i] for i in range(len(self.columns))}
            gui_data.append(row_dict)

        if not gui_data:
            messagebox.showerror("Error", "No DID data to generate. Please add data or load a CSV.")
            return

        # --- Process GUI data into the format needed for generation ---
        dids_data = defaultdict(list)
        for row in gui_data:
            if not row['DID']: # Skip empty rows
                continue
            dids_data[row['DID']].append({
                'SignalName': row['SignalName'],
                'DataType': row['DataType'],
                'Size': row['Size'],
                'Session': row['Session'],
                'SecurityLevel': row['SecurityLevel']
            })
        
        self.status_var.set(f"Generating DEXT for {len(dids_data)} DIDs...")
        self._run_generation_logic(dids_data)

    def _run_generation_logic(self, dids_data):
        """The core logic to build and save the ARXML file."""
        ET.register_namespace('', AUTOSAR_NAMESPACE)
        root = ET.Element("AUTOSAR", { f"{{{XSI_NAMESPACE}}}schemaLocation": SCHEMA_LOCATION })
        ar_packages = ET.SubElement(root, "AR-PACKAGES")

        dext_elements = self._create_ar_package(ar_packages, "MyECU_DiagnosticExtract")
        data_elements_package = self._create_ar_package(ar_packages, "MyECU_DataElements")
        data_types_package = self._create_ar_package(ar_packages, "MyECU_DataTypes")
        access_perms_package = self._create_ar_package(ar_packages, "MyECU_AccessPermissions")

        # Create common access permissions
        ET.SubElement(access_perms_package, "DIAGNOSTIC-SESSION-CONTROL").set("SHORT-NAME", "Default_Session")
        ET.SubElement(access_perms_package, "DIAGNOSTIC-SESSION-CONTROL").set("SHORT-NAME", "Extended_Session")
        ET.SubElement(access_perms_package, "DIAGNOSTIC-SECURITY-LEVEL").set("SHORT-NAME", "No_Security")
        ET.SubElement(access_perms_package, "DIAGNOSTIC-SECURITY-LEVEL").set("SHORT-NAME", "Level_1")
        
        for did_name, signals in dids_data.items():
            try:
                did_hex = did_name.split('_')[1]
                did_dec = str(int(did_hex, 16))
            except (IndexError, ValueError):
                messagebox.showerror("Error", f"Could not parse DID number from '{did_name}'. Aborting.")
                return

            did_element = ET.SubElement(dext_elements, "DIAGNOSTIC-DATA-IDENTIFIER")
            ET.SubElement(did_element, "SHORT-NAME").text = did_name
            ET.SubElement(did_element, "ID").text = did_dec
            data_element_refs = ET.SubElement(did_element, "DATA-ELEMENT-REFS")

            for signal in signals:
                signal_name = signal['SignalName']
                data_element = ET.SubElement(data_elements_package, "DATA-ELEMENT-PROTOTYPE")
                ET.SubElement(data_element, "SHORT-NAME").text = signal_name
                
                type_name = self._create_implementation_data_type(data_types_package, signal)
                ET.SubElement(data_element, "TYPE-TREF", DEST="IMPLEMENTATION-DATA-TYPE").text = f"/MyECU_DataTypes/{type_name}"
                
                ET.SubElement(data_element_refs, "DATA-ELEMENT-REF", DEST="DATA-ELEMENT-PROTOTYPE").text = f"/MyECU_DataElements/{signal_name}"

                mapping = ET.SubElement(dext_elements, "DIAGNOSTIC-SERVICE-DATA-MAPPING")
                ET.SubElement(mapping, "SHORT-NAME").text = f"{signal_name}_Mapping"
                ET.SubElement(mapping, "DATA-ELEMENT-PROTOTYPE-REF", DEST="DATA-ELEMENT-PROTOTYPE").text = f"/MyECU_DataElements/{signal_name}"
            
            session = signals[0]['Session'].replace(" ", "_")
            security = signals[0]['SecurityLevel'].replace(" ", "_")
            
            access_perm = ET.SubElement(access_perms_package, "DIAGNOSTIC-ACCESS-PERMISSION")
            ET.SubElement(access_perm, "SHORT-NAME").text = f"{did_name}_Read_Access"
            ET.SubElement(access_perm, "SERVICE-REF", DEST="DIAGNOSTIC-SERVICE-CLASS").text = "/AUTOSAR_Dcm/DiagnosticServices/ReadDataByIdentifier"
            
            did_ref = ET.SubElement(access_perm, "DIAG-DATA-IDENTIFIER-REFS")
            ET.SubElement(did_ref, "DIAG-DATA-IDENTIFIER-REF", DEST="DIAGNOSTIC-DATA-IDENTIFIER").text = f"/MyECU_DiagnosticExtract/{did_name}"

            sessions = ET.SubElement(access_perm, "SESSIONS")
            ET.SubElement(sessions, "SESSION-REF", DEST="DIAGNOSTIC-SESSION-CONTROL").text = f"/MyECU_AccessPermissions/{session}"
            
            security_levels = ET.SubElement(access_perm, "SECURITY-LEVELS")
            ET.SubElement(security_levels, "SECURITY-LEVEL-REF", DEST="DIAGNOSTIC-SECURITY-LEVEL").text = f"/MyECU_AccessPermissions/{security}"

        try:
            xml_str = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(xml_str)
            pretty_xml_str = reparsed.toprettyxml(indent="    ", encoding="utf-8")

            with open(ARXML_OUTPUT_FILE, 'wb') as f:
                f.write(pretty_xml_str)
            
            self.status_var.set(f"Successfully generated DEXT file: '{ARXML_OUTPUT_FILE}'")
            messagebox.showinfo("Success", f"DEXT file '{ARXML_OUTPUT_FILE}' has been generated successfully.")
        except Exception as e:
            messagebox.showerror("Generation Error", f"An error occurred while generating the file: {e}")
            self.status_var.set("Error during file generation.")

    def _create_ar_package(self, parent, short_name):
        ar_package = ET.SubElement(parent, "AR-PACKAGE")
        ET.SubElement(ar_package, "SHORT-NAME").text = short_name
        return ET.SubElement(ar_package, "ELEMENTS")

    def _create_implementation_data_type(self, parent, signal_info):
        data_type = signal_info['DataType']
        size = signal_info['Size']
        short_name = f"{signal_info['SignalName']}_Type"
        
        if data_type.lower() == 'string':
            impl_data_type = ET.SubElement(parent, "IMPLEMENTATION-DATA-TYPE")
            ET.SubElement(impl_data_type, "SHORT-NAME").text = short_name
            ET.SubElement(impl_data_type, "CATEGORY").text = "ARRAY"
            sw_data_def_props = ET.SubElement(impl_data_type, "SW-DATA-DEF-PROPS")
            variants = ET.SubElement(sw_data_def_props, "SW-DATA-DEF-PROPS-VARIANTS")
            conditional = ET.SubElement(variants, "SW-DATA-DEF-PROPS-CONDITIONAL")
            ET.SubElement(conditional, "BASE-TYPE-REF", DEST="IMPLEMENTATION-DATA-TYPE").text = "/AUTOSAR_Platform/ImplementationDataTypes/uint8"
            
            sub_elements = ET.SubElement(impl_data_type, "SUB-ELEMENTS")
            element = ET.SubElement(sub_elements, "IMPLEMENTATION-DATA-TYPE-ELEMENT")
            ET.SubElement(element, "SHORT-NAME").text = f"{signal_info['SignalName']}_Byte"
            ET.SubElement(element, "CATEGORY").text = "TYPE_REFERENCE"
            ET.SubElement(element, "ARRAY-SIZE").text = str(size)
            sw_data_def_props_elem = ET.SubElement(element, "SW-DATA-DEF-PROPS")
            variants_elem = ET.SubElement(sw_data_def_props_elem, "SW-DATA-DEF-PROPS-VARIANTS")
            conditional_elem = ET.SubElement(variants_elem, "SW-DATA-DEF-PROPS-CONDITIONAL")
            ET.SubElement(conditional_elem, "IMPLEMENTATION-DATA-TYPE-REF", DEST="IMPLEMENTATION-DATA-TYPE").text = "/AUTOSAR_Platform/ImplementationDataTypes/uint8"
        else:
            impl_data_type = ET.SubElement(parent, "IMPLEMENTATION-DATA-TYPE")
            ET.SubElement(impl_data_type, "SHORT-NAME").text = short_name
            ET.SubElement(impl_data_type, "CATEGORY").text = "VALUE"
            sw_data_def_props = ET.SubElement(impl_data_type, "SW-DATA-DEF-PROPS")
            variants = ET.SubElement(sw_data_def_props, "SW-DATA-DEF-PROPS-VARIANTS")
            conditional = ET.SubElement(variants, "SW-DATA-DEF-PROPS-CONDITIONAL")
            base_type_ref = f"/AUTOSAR_Platform/ImplementationDataTypes/{data_type}"
            ET.SubElement(conditional, "BASE-TYPE-REF", DEST="IMPLEMENTATION-DATA-TYPE").text = base_type_ref
            
        return short_name


if __name__ == "__main__":
    app = DextGeneratorApp()
    app.mainloop()
