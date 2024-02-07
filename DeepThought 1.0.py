import pandas as pd
import itertools
import tkinter as tk
from tkinter import ttk, filedialog


class Screen:
    root = tk.Tk()
    def __init__(self, *, dataframe=None, PFD_dwell=None,
                 organic_dwell=None, pause_after_pump_stop=None,
                 repeats=None):
        self.dataframe = dataframe
        self.PFD_dwell = PFD_dwell
        self.organic_dwell = organic_dwell
        self.pause_after_pump_stop = pause_after_pump_stop
        self.repeats = repeats
        self.tracer_well_coordinates = None
        self.wash_well_coordinates = None
        self.combinations = None
        self.combinations_names = None
        self.clas = None

    @classmethod
    def load_variables(cls):
        input_window_load_vars = tk.Toplevel(cls.root)
        input_window_load_vars.title("Inputs")
        cls.root.withdraw()

        # Variables to store user inputs
        PFD_dwell_var = tk.DoubleVar()
        organic_dwell_var = tk.DoubleVar()
        pause_after_pump_stop_var = tk.DoubleVar()
        repeats_var = tk.IntVar()

        # Function to get values and close the window
        def get_inputs():
            cls.PFD_dwell = PFD_dwell_var.get()
            cls.organic_dwell = organic_dwell_var.get()
            cls.pause_after_pump_stop = pause_after_pump_stop_var.get()
            cls.repeats = repeats_var.get()

            input_window_load_vars.destroy()

        # Create and layout the input fields
        labels = ["PFD Dwell Time (s)", "Organic Dwell Time (s)", "Pause Time After Pump Stop (s)", "Droplet Multiplicity"]
        variables = [PFD_dwell_var, organic_dwell_var, pause_after_pump_stop_var, repeats_var]

        for i, label in enumerate(labels):
            ttk.Label(input_window_load_vars, text=label).grid(row=i, column=0, padx=10, pady=10, sticky="e")
            ttk.Entry(input_window_load_vars, textvariable=variables[i]).grid(row=i, column=1, padx=10, pady=10)

        # Button to get values
        ttk.Button(input_window_load_vars, text="Upload", command=get_inputs).grid(row=len(labels), column=0, columnspan=2, pady=10)

        cls.root.wait_window(input_window_load_vars)

        file_path_template_csv = filedialog.askopenfilename(title="Select a CSV File", filetypes=[('CSV files', '*.csv')])
        if file_path_template_csv:
            dataframe = pd.read_csv(file_path_template_csv)
        return cls(
            dataframe=dataframe,PFD_dwell=cls.PFD_dwell,
            organic_dwell=cls.organic_dwell,
            pause_after_pump_stop=cls.pause_after_pump_stop,
            repeats=cls.repeats)

    def initialize(self):  # This takes the input .csv file and makes combinations with it
        required_attributes = ['dataframe', 'PFD_dwell', 'organic_dwell', 'pause_after_pump_stop', 'repeats']

        try:
            if any(getattr(self, attr, None) is None for attr in required_attributes):
                raise AttributeError(
                    f"Error: Missing one or more required attributes: {', '.join(required_attributes)}. Did you load variables?")

            def append_coordinates():
                coordinates = []
                for i in self.dataframe.index:
                    coordinates.append((self.dataframe.x[i], self.dataframe.y[i]))
                self.dataframe['coordinates'] = coordinates

            append_coordinates()

            self.dataframe = self.dataframe.dropna().reset_index(drop=True)

            columns = list(map(str, self.dataframe.plate_column.tolist()))
            rows = self.dataframe.plate_row.tolist()
            coordinates = self.dataframe.coordinates.tolist()
            wells_coords = [(r + c, (coord)) for r, c, coord in zip(rows, columns, coordinates)]
            names = self.dataframe.chemical_name.tolist()
            word_fragments_to_remove = ['trace', 'wash', 'mark', 'rinse']  # Omits tracer and wash wells from being included in screen combos
            mask = self.dataframe['class'].str.lower().str.contains('|'.join(word_fragments_to_remove))
            elements_to_remove = self.dataframe.loc[mask, 'class'].tolist()
            self.clas = list(self.dataframe['class'].unique())
            self.clas = [x for x in self.clas if x.lower() not in elements_to_remove]

            components = self.clas  # list of all the individual types of reagent classes

            components_coords = [
                [w for w in wells_coords if self.dataframe.loc[wells_coords.index(w), 'class'] == c] for c in components
            ]
            self.combinations = list(itertools.product(*components_coords))  # list of all the combinations

            wells_names = [(r + c, (name)) for r, c, name in zip(rows, columns, names)]
            components_names = [
                [w for w in wells_names if self.dataframe.loc[wells_names.index(w), 'class'] == c] for c in components
            ]
            self.combinations_names = list(itertools.product(*components_names))

            tracer_entry = self.dataframe.loc[self.dataframe['class'].str.lower().str.contains('trace|mark')]
            if not tracer_entry.empty:
                self.tracer_well_coordinates = tuple(tracer_entry[['x', 'y']].values[0])
            else:
                print("No Tracer included: Did you want to include a tracer droplet?")

            wash_entry = self.dataframe.loc[self.dataframe['class'].str.lower().str.contains('wash|rinse')]
            if not wash_entry.empty:
                self.wash_well_coordinates = tuple(wash_entry[['x','y']].values[0])

        except AttributeError as e:
            print(e)

        if len(self.combinations)*self.repeats == 69:
            print(f"{len(self.combinations)*self.repeats} droplets...Nice")
        else:
            print(f"FYI: {len(self.combinations) * self.repeats} droplets will be made")

    def combine(self):  # this writes a .txt file for the GCode commands
        required_attributes = ['combinations', 'repeats', 'PFD_dwell', 'organic_dwell', 'pause_after_pump_stop']
        try:
            if any(getattr(self, attr, None) is None for attr in required_attributes):
                raise AttributeError(f"Error: One or more required attributes does not exist: {', '.join(required_attributes)}. Did you upload a well plate template and initialize the screen?")

            file_path_save_gcode = filedialog.asksaveasfilename(title="Select a path to save",
                                                                filetypes=[('Text files', '*.txt')])
            try:
                if file_path_save_gcode:
                    with open(file_path_save_gcode, 'w') as file:
                        for i in range(len(self.combinations)):  # for every combination
                            for j in range(self.repeats):  # range of repeats you want to make
                                for k in range(len(self.combinations[1])):  # first entry of each combo. In this case, PFD well must be in A1 because it's always sampled first
                                    if k == 0:
                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000 PFD\n') # Sample PFD Well
                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z-5.5 F3000\n')
                                        file.write("M4")
                                        file.write(f'G04 P{self.PFD_dwell}\n')
                                        file.write("M3")
                                        file.write(f'G04 P{self.pause_after_pump_stop}\n')
                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000\n\n')

                                        file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z0.0 F3000 Rinse\n') #Tip Rinse
                                        file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z-5.5 F3000\n')
                                        file.write(f'G01 P{self.pause_after_pump_stop}\n')
                                        file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z-0.0 F3000\n\n')

                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000 PFD\n') # Sample PFD Well
                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z-5.5 F3000\n')
                                        file.write("M4")
                                        file.write(f'G04 P{self.PFD_dwell}\n')
                                        file.write("M3")
                                        file.write(f'G04 P{self.pause_after_pump_stop}\n')
                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000\n\n')

                                    else:  # when not the first ingredient in a combo, use organic dwell. Again, this assumes the first well sampled in every combo is PFD
                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000 Organic\n') #Sample organic well
                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z-5.5 F3000\n')
                                        file.write("M4")
                                        file.write(f'G04 P{self.organic_dwell}\n')
                                        file.write("M3")
                                        file.write(f'G04 P{self.pause_after_pump_stop}\n')
                                        file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000\n\n')

                                        file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z0.0 F3000 Rinse\n') #Tip Rinse
                                        file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z-5.5 F3000\n')
                                        file.write(f'G01 P{self.pause_after_pump_stop}\n')
                                        file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z-0.0 F3000\n\n')

                                if (i*self.repeats + j + 1) % 10 == 0:  # samples from tracer well after every 10th combination. Comment out if not needed.

                                    file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000 PFD\n')  # Sample PFD Well
                                    file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z-5.5 F3000\n')
                                    file.write("M4")
                                    file.write(f'G04 P{self.PFD_dwell}\n')
                                    file.write("M3")
                                    file.write(f'G04 P{self.pause_after_pump_stop}\n')
                                    file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000\n\n')

                                    file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z0.0 F3000 Rinse\n')  # Tip Rinse
                                    file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z-5.5 F3000\n')
                                    file.write(f'G01 P{self.pause_after_pump_stop}\n')
                                    file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z-0.0 F3000\n\n')

                                    file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000 PFD\n')  # Sample PFD Well
                                    file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z-5.5 F3000\n')
                                    file.write("M4")
                                    file.write(f'G04 P{self.PFD_dwell}\n')
                                    file.write("M3")
                                    file.write(f'G04 P{self.pause_after_pump_stop}\n')
                                    file.write(f'G01 X{self.combinations[i][k][1][0]} Y{self.combinations[i][k][1][1]} Z0.0 F3000\n\n')

                                    file.write(f'G01 X{self.tracer_well_coordinates[0]} Y{self.tracer_well_coordinates[1]} Z0.0 F3000 Tracer\n') # Sample Tracer Well
                                    file.write(f'G01 X{self.tracer_well_coordinates[0]} Y{self.tracer_well_coordinates[1]} Z-5.5 F3000\n')
                                    file.write(f'G04 P{self.organic_dwell}\n')
                                    file.write(f'G04 P{self.pause_after_pump_stop}\n')
                                    file.write(f'G01 X{self.tracer_well_coordinates} Y{self.tracer_well_coordinates} Z0.0 F3000\n\n')

                                    file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z0.0 F3000 Rinse\n')  # Tip Rinse
                                    file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z-5.5 F3000\n')
                                    file.write(f'G01 P{self.pause_after_pump_stop}\n')
                                    file.write(f'G01 X{self.wash_well_coordinates[0]} Y{self.wash_well_coordinates[1]} Z-0.0 F3000\n\n')

                else:
                    raise AttributeError
            except AttributeError:
                print('Error: No Save File Path Given')
        except AttributeError as e:
            print(e)

    def visualize(self): # This writes a .csv file of all the combinations to keep track of what's in each droplet
        required_attributes = ['combinations_names', 'clas']
        try:
            if any(getattr(self, attr, None) is None for attr in required_attributes):
                raise AttributeError(
                    f"Error: One or more required attributes does not exist: {', '.join(required_attributes)}. Did you upload a well plate template and initialize the screen?")
            df_combinations = pd.DataFrame(self.combinations_names, columns=self.clas)
            df_combinations = df_combinations.loc[df_combinations.index.repeat(3)].reset_index(drop=True)  # repeats the index a certain number of times to match the number of times you want to form a reaction
            df_combinations.index += 1
            column_names = df_combinations.columns.values
            df_combinations[column_names] = df_combinations.apply(lambda x: tuple([val[1] for val in x]))  # drops the well number associated with a reagent in each cell
            col = [a + 1 for a in range(len(df_combinations.index))]
            df_combinations.insert(0, 'reaction #', col)
            file_path_save_vizualization = filedialog.asksaveasfilename(title = "Select a path to save",
                                                                             filetypes=[('CSV file', '*.csv')])
            try:
                if file_path_save_vizualization:
                    df_combinations.to_csv(file_path_save_vizualization)
            except:
                print('No Save File Path Given')

        except AttributeError as e:
            print(e)

"""I can no longer sit back and allow Communist infiltration, Communist indoctrination, 
Communist subversion, and the international Communist conspiracy 
to sap and impurify all of our precious bodily fluids. –Brig. Gen. Jack D. Ripper"""

#            o
#            |
#          ,'~'.
#         /     \
#        |   ____|_
#        |  '___,,_'         .----------------.
#        |  ||(o |o)|       ( KILL ALL HUMANS! )
#        |   -------         ,----------------'
#        |  _____|         -'
#        \  '####,
#         -------
#       /________\
#     (  )        |)
#     '_ ' ,------|\         _
#    /_ /  |      |_\        ||
#   /_ /|  |     o| _\      _||
#  /_ / |  |      |\ _\____//' |
# (  (  |  |      | (_,_,_,____/
#  \ _\ |   ------|
#   \ _\|_________|
#    \ _\ \__\\__\
#    |__| |__||__|
# ||/__/  |__||__|
#         |__||__|
#         |__||__|
#         /__)/__)
#        /__//__/
#       /__//__/
#      /__//__/.
#    .'    '.   '.
#   (_kOs____)____)


