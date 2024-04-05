import sqlite3
import yaml
import re
from itertools import tee, chain
from string import Template
from datetime import datetime
from pathlib import Path

class DataBase:
    def __init__(self, database_file, table_name, man_fields):

        # Class variables
        self.table_name = table_name
        self.man_fields = man_fields
        self.conn = None
        self.cursor = None

        try:
            if database_file.exists():
                self.conn = sqlite3.connect(database_file)
                self.cursor = self.conn.cursor()
                print("Successfully connected to the database.")
                if not self.__check_table_schema():
                    print('Table schema does not have all mandatory fields')
                    raise sqlite3.Error
            else:
                print(f"Error - DB path is wrong: {database_file}")
                raise sqlite3.Error
        except sqlite3.Error as e:
            print("Error connecting to the database.", e)
            exit(1)
    
    def __del__(self):
        if self.cursor:
            self.cursor.close()
            self.conn.close()
            print("Database connection closed.")

    def __check_table_schema(self):
        ''' Check mandatory fields exist in the table
        '''
        schema = self.query(f"PRAGMA table_info({self.table_name})")
        existing_fields = [field for schema_tuple in schema for field in self.man_fields if field in schema_tuple]

        if sorted(self.man_fields) == sorted(existing_fields):
            return True
        else:
            return False
    
    def query(self, query):
        return self.cursor.execute(query).fetchall()

def load_config(path):
    try:
        with open(f"{path}/config.yml", "r") as yamlfile:
            config = yaml.load(yamlfile, Loader=yaml.FullLoader)
            db_path = Path(f"{path}/{config[0]['config']['database']['path']}")
            srpt_path = Path(f"{path}/{config[0]['config']['template']['path']}")
            return config, db_path, srpt_path
        
    except Exception as e:
        print(f"Unable to load file: \n {e}")

def get_raw_cmds(query_res, regex, script_tpl):
    ''' Gets the query results in the form of a list of tuples, applies the regex to the message
        and writes the corresponding script lines into tupple
    '''

    return [
        [column[0], column[1], script_tpl.replace('<ARG>', re.search(regex, column[3]).group(0))]
        for column in query_res if regex and re.search(regex, column[3])
    ]

def previous_and_next(some_iterable):
    prevs, items = tee(some_iterable, 2)
    prevs = chain([None], prevs)
    return zip(prevs, items)

def get_commands(config, db_path):

    # Load database
    db_name = config[0]['config']['database']['table_name']
    mandatory_fields = config[0]['config']['database']['mandatory_fields']
    db = DataBase(db_path, db_name, mandatory_fields)

    # Get generation config
    delay_mode = config[0]['config']['delay']['mode'].lower()
    delay_value = str(config[0]['config']['delay']['value'])

    # Get all script cmds
    script_cmds = [cmd for q in config[1:] for cmd in get_raw_cmds(
        db.query(q['query']['sql']),
          q['query']['regex'],
          q['query']['script'])]

    # Sort cmds by Id - ensure cmd order is respected
    script_cmds.sort(key=lambda tup: tup[0])

    # Adds relative delays between commands
    i = 0
    for prev, curr in previous_and_next(script_cmds):
        if prev:
            delay = str(round(curr[1]-prev[1])) if (delay_mode == 'inherited') else delay_value
            script_cmds[i][2] = curr[2].replace('<DELAY>', delay).strip()
        else:
            script_cmds[i][2] = curr[2].replace('<DELAY>', '0').strip()
        i += 1

    # Keep script lines only
    script_cmds_only = [cmd[2] for cmd in script_cmds]

    return script_cmds_only

def write_script(path):

    start = datetime.now()

    # Load yaml config from data folder and paths
    config, db_path, srpt_path = load_config(path)

    # Get script commands
    script_cmds = get_commands(config, db_path)

    # Write replacer dictonary
    d = {
        'date': f'Generated on: {start.strftime("%d/%m/%Y %H:%M:%S")}',
        'db_file': f'Generated from: {db_path}',
        'cmd_list': '\n\n'.join(script_cmds)
    }

    # Open template script and write to string
    print(srpt_path)
    with open(srpt_path, 'r') as f:
        src = Template(f.read())
        result = src.substitute(d)
        f.close()
        print(f'Generated script: \n{result}')
    
    # Open output script and write string to file
    output_file = f"script-{start.strftime("%d.%m.%Y-%H.%M.%S")}{srpt_path.suffix}"
    with open(output_file, "a") as f:
        f.write(result)
        print(f'Saved script to {output_file}')
        f.close()
    
    end = datetime.now()
    print(f"Elapsed time: {end-start}")

if __name__ == "__main__":

    # Build path
    rel_path = Path("data/")
    if not rel_path.exists():
        rel_path = Path("example_data/")
        print("Data directory does not exist. Using example data.")

    write_script(rel_path)
