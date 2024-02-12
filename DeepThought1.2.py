import pandas as pd
import itertools
import tkinter as tk
from tkinter import ttk, filedialog
import datetime
import plotly.graph_objects as go
import numpy as np



class Screen:
    root = tk.Tk()
    def __init__(self, *, dataframe=None, PFD_dwell=None,
                 organic_dwell=None, pause_after_pump_stop=None,
                 repeats=None, feedrate = None):

        self.dataframe = dataframe
        self.PFD_dwell = PFD_dwell
        self.organic_dwell = organic_dwell
        self.pause_after_pump_stop = pause_after_pump_stop
        self.repeats = repeats
        self.feedrate = feedrate
        self.PFD_well_coordinates = None
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
        feedrate_var = tk.IntVar()

        # Function to get values and close the window
        def get_inputs():
            cls.PFD_dwell = PFD_dwell_var.get()
            cls.organic_dwell = organic_dwell_var.get()
            cls.pause_after_pump_stop = pause_after_pump_stop_var.get()
            cls.repeats = repeats_var.get()
            cls.feedrate = feedrate_var.get()

            input_window_load_vars.destroy()

        # Create and layout the input fields
        labels = ["PFD Dwell Time (s)", "Organic Dwell Time (s)", "Pause Time After Pump Stop (s)", "Droplet Multiplicity", "Motor Feedrate (mm/min)"]
        variables = [PFD_dwell_var, organic_dwell_var, pause_after_pump_stop_var, repeats_var, feedrate_var]

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
            dataframe=dataframe,
            PFD_dwell=cls.PFD_dwell,
            organic_dwell=cls.organic_dwell,
            pause_after_pump_stop=cls.pause_after_pump_stop,
            repeats=cls.repeats,
            feedrate=cls.feedrate)

    def initialize(self):  # This takes the input .csv file and makes combinations with it
        required_attributes = ['dataframe', 'PFD_dwell', 'organic_dwell', 'pause_after_pump_stop', 'repeats']

        try:
            if any(getattr(self, attr, None) is None for attr in required_attributes):
                raise AttributeError(
                    f"Error: Missing one or more required attributes: {', '.join(required_attributes)}. Did you load variables?")

            df = self.dataframe
            coords = []
            for i in df.index:
                coords.append((df.x[i], df.y[i]))
            df['coordinates'] = coords

            df = df.dropna().reset_index(drop=True)

            columns = list(map(str, df.plate_column.tolist()))
            rows = df.plate_row.tolist()
            coordinates = df.coordinates.tolist()
            wells_coords = [(r + c, coord) for r, c, coord in zip(rows, columns, coordinates)]
            names = df.chemical_name.tolist()

            word_fragments_to_remove = ['trace', 'wash', 'mark', 'rinse', 'pfd', 'perfluorodecalin', 'oil']  # Omits tracer, carrier fluid, and wash wells from being included in screen combos
            mask = df['class'].str.lower().str.contains('|'.join(word_fragments_to_remove))
            elements_to_remove = df.loc[mask, 'class'].str.lower().tolist()
            self.clas = list(df['class'].unique())
            self.clas = [x for x in self.clas if x.lower() not in elements_to_remove]

            components = self.clas  # list of all the individual types of reagent classes

            components_coords = [[w for w in wells_coords if df.loc[wells_coords.index(w), 'class'] == c] for c in components]
            self.combinations = list(itertools.product(*components_coords))  # list of all the combinations

            wells_names = [(r + c, name) for r, c, name in zip(rows, columns, names)]
            components_names = [[w for w in wells_names if df.loc[wells_names.index(w), 'class'] == c] for c in components]
            self.combinations_names = list(itertools.product(*components_names))

            tracer_entry = df.loc[df['class'].str.lower().str.contains('trace|mark')]
            if not tracer_entry.empty:
                self.tracer_well_coordinates = tuple(tracer_entry[['x', 'y']].values[0])
            else:
                print("No Tracer included: Did you want to include a tracer droplet?")

            wash_entry = df.loc[df['class'].str.lower().str.contains('wash|rinse')]
            if not wash_entry.empty:
                self.wash_well_coordinates = tuple(wash_entry[['x','y']].values[0])

            PFD_entry = df.loc[df['class'].str.lower().str.contains('pfd|perfluorodecalin|oil')]
            if not PFD_entry.empty:
                self.PFD_well_coordinates = tuple(PFD_entry[['x' , 'y']].values[0])

        except AttributeError as e:
            print(e)

        if len(self.combinations)*self.repeats == 69:
            print(f"{len(self.combinations)*self.repeats} droplets...Nice")
        else:
            print(f"FYI: {len(self.combinations) * self.repeats} droplets will be made")

    def combine(self):  # this writes a .txt file for the GCode commands
        def sample_well(x_coord, y_coord, dwell_time, pause, feedrate):
            file.write(f'G01 X{x_coord} Y{y_coord}, Z0.0 F{feedrate}\n')
            file.write(f'G01 X{x_coord} Y{y_coord}, Z-5.5 F{feedrate}\n')
            file.write('M4\n')
            file.write(f'G04 P{dwell_time}\n')
            file.write('M3\n')
            file.write(f'G04 P{pause}\n')
            file.write(f'G01 X{x_coord}, Y{y_coord} Z0.0 F{feedrate}\n\n')
        def tip_rinse(x_coord,y_coord, pause, feedrate):
            file.write(f'G01 X{x_coord} Y{y_coord} Z0.0 F{feedrate}\n')
            file.write(f'G01 X{x_coord} Y{y_coord} Z-5.5 F{feedrate}\n')
            file.write(f'G04 P{pause}\n')
            file.write(f'G01 X{x_coord} Y{y_coord} Z0.0 F{feedrate}\n\n')

        required_attributes = ['combinations', 'repeats', 'PFD_dwell', 'organic_dwell', 'pause_after_pump_stop', 'feedrate']
        try:
            if any(getattr(self, attr, None) is None for attr in required_attributes):
                raise AttributeError(f"Error: One or more required attributes does not exist: {', '.join(required_attributes)}. Did you upload a well plate template and initialize the screen?")

            file_path_save_gcode = filedialog.asksaveasfilename(title="Select a path to save",
                                                                filetypes=[('Text files', '*.txt')])
            date_created = datetime.date.today().strftime('%b-%d-%Y')
            directory_with_file , extension = file_path_save_gcode.split("." , 1)
            gcode_file_path = (f"{directory_with_file} {date_created}.{extension}")

            try:
                if gcode_file_path:
                    with open(gcode_file_path, 'w') as file:
                        for i in range(len(self.combinations)):  # for every combination
                            for j in range(self.repeats):  # range of repeats you want to make
                               sample_well(self.PFD_well_coordinates[0], self.PFD_well_coordinates[1], self.PFD_dwell, self.pause_after_pump_stop, self.feedrate) # Sample carrier fluid
                               tip_rinse(self.wash_well_coordinates[0], self.wash_well_coordinates[1], self.pause_after_pump_stop, self.feedrate) # Tip rinse
                               sample_well(self.PFD_well_coordinates[0], self.PFD_well_coordinates[1], self.PFD_dwell, self.pause_after_pump_stop, self.feedrate) # Sample carrier fluid
                               for k in range(len(self.combinations[1])):  # Each well in a combination (combinations don't include carrier fluid)
                                    sample_well(self.combinations[i][k][1][0], self.combinations[i][k][1][1], self.organic_dwell, self.pause_after_pump_stop, self.feedrate) # Sample stock solution
                                    tip_rinse(self.wash_well_coordinates[0], self.wash_well_coordinates[1], self.pause_after_pump_stop, self.feedrate) # Tip Rinse
                               if (i*self.repeats + j + 1) % 10 == 0:  # samples from tracer well after every 10th total combination.
                                   sample_well(self.PFD_well_coordinates[0] , self.PFD_well_coordinates[1] ,self.PFD_dwell , self.pause_after_pump_stop, self.feedrate) # Sample carrier fluid
                                   tip_rinse(self.wash_well_coordinates[0] , self.wash_well_coordinates[1] ,self.pause_after_pump_stop, self.feedrate) # Tip rinse
                                   sample_well(self.PFD_well_coordinates[0] , self.PFD_well_coordinates[1] ,self.PFD_dwell , self.pause_after_pump_stop, self.feedrate) # Sample carrier fluid
                                   sample_well(self.tracer_well_coordinates[0], self.tracer_well_coordinates[1], self.organic_dwell, self.pause_after_pump_stop, self.feedrate) # Sample tracer well
                                   tip_rinse(self.wash_well_coordinates[0] , self.wash_well_coordinates[1] ,self.pause_after_pump_stop, self.feedrate) # Tip rinse
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
                raise AttributeError(f"Error: One or more required attributes does not exist: {', '.join(required_attributes)}. Did you upload a well plate template and initialize the screen?")
            df_combinations = pd.DataFrame(self.combinations_names, columns=self.clas)
            df_combinations = df_combinations.loc[df_combinations.index.repeat(self.repeats)].reset_index(drop=True)  # repeats the index a certain number of times to match the number of times you want to form a reaction
            df_combinations.index += 1
            column_names = df_combinations.columns.values
            df_combinations[column_names] = df_combinations.apply(lambda x: tuple([val[1] for val in x]))  # drops the well number associated with a reagent in each cell
            rxn_num = [a + 1 for a in range(len(df_combinations.index))]
            df_combinations.insert(0, 'reaction #', rxn_num)
            file_path_save_vizualization = filedialog.asksaveasfilename(title = "Select a path to save", filetypes=[('CSV file', '*.csv')])
            try:
                if file_path_save_vizualization:
                    date_created = datetime.date.today().strftime('%b-%d-%Y')
                    directory_with_file, extension = file_path_save_vizualization.split(".", 1)
                    visualization_file_path = (f"{directory_with_file} {date_created}.{extension}")
                    df_combinations.to_csv(visualization_file_path)
            except:
                print('No Save File Path Given')

        except AttributeError as e:
            print(e)

    def plate_summary(self): # Note: this is going to give a weird output because empty wells are dropped in self.dataframe
        df = self.dataframe

        # Create a scatter plot with a single trace
        fig = go.Figure()

        blues = [ '#edf5ff', '#001141', '#001d6c', '#002d9c', '#0043ce', '#0f62fe', '#4589ff', '#78a9ff', '#a6c8ff', '#d0e2ff']
        purples = ['#edf5ff', '#1c0f30', '#31135e', '#491d8b', '#6929c4', '#8a3ffc', '#a56eff', '#be95ff', '#d4bbff', '#e8daff','#f6f2ff']
        teals = ['#edf5ff', '#081a1c', '#022b30', '#004144', '#005d5d', '#007d79', '#009d9a', '#08bdba', '#3ddbd9', '#9ef0f0', '#d9fbfb']

        # Accumulate data points in a single trace
        trace = go.Scatter(
            x=df['plate_column'] ,
            y=df['plate_row'] ,
            mode='markers' ,
            marker=dict(
                size=20 ,
                color=df['class'].astype('category').cat.codes ,
                colorscale=blues,
                line=dict(color='black' , width=1) ,
            ) ,
            customdata=df[['chemical_name' , 'class' , 'smiles']] ,
            text=df.apply(
                lambda row: f"Chemical: {row['chemical_name']}<br>Class: {row['class']}<br>SMILES: {row['smiles']}" ,
                axis=1
                ) ,
            hoverinfo='text' ,
        )

        # Add the trace to the figure
        fig.add_trace(trace)

        # Customize the layout
        fig.update_layout(
            title='Well Plate Layout' ,
            xaxis_title='Column' ,
            yaxis_title='Row' ,
            xaxis=dict(tickmode='array' , tickvals=list(df['plate_column'].unique()) ,
                       ticktext=df['plate_column'].unique()
                       ) ,
            yaxis=dict(tickmode='array' , tickvals=list(df['plate_row'].unique()) , ticktext=df['plate_row'].unique()) ,
        )

        # Show the interactive plot
        fig.show()


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
