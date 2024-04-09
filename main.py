import yaml
import os
import re
from string import Template
from datetime import datetime
from pathlib import Path
from sqlite import Sqlite
from utils import previous_and_next

def load_config(path: Path):
    ''' Gets path to config folder and loads yaml data structure.
    '''
    try:
        with open(f"{path}/config.yml", "r") as yamlfile:
            config = yaml.load(yamlfile, Loader=yaml.FullLoader)
            db_path = Path(f"{path}/{config[0]['config']['database']['path']}")
            srpt_path = Path(f"{path}/{config[0]['config']['template']['path']}")
            return config, db_path, srpt_path
        
    except Exception as e:
        print(f"Unable to load file: \n {e}")

def get_raw_cmds(query_res: list, regex: str, script_tpl: str) -> tuple:
    ''' Gets the query results in the form of a list of tuples, applies the regex to the message
        and writes the corresponding script lines into tupple
    '''
    return [
        [column[0], column[1], script_tpl.replace('<ARG>', re.search(regex, column[3]).group(0))]
        for column in query_res if regex and re.search(regex, column[3])
    ]

def get_commands(config, db_path: Path) -> list:
    ''' This function generates the script commands. It queries the dabatase, applies the corresponding
        regex and writes the result in to the script command   

        Parameters:
                - config: the yaml data structure
                - db_path: relative path to the db file
        
        Synopsis:
            This function does the following:
                - Load database class
                - For each query in the db, run the corresponding query and get the script command
                - Order command list by field in query tuple(0) - usually the log entry id
                - Compute the delay between commands - if ihnerited computes the diference in time
                between the current command and the previous using the time stamps and writes it into
                the <DELAY> key in the script
                - Removes unessessary fiels from the commands list - keeps only the script
    '''

    # Load database
    config_z = config[0]['config']
    db_name = config_z['database']['table_name']
    mandatory_fields = config_z['database']['mandatory_fields']
    db = Sqlite(db_path, db_name, mandatory_fields)

    # Get generation config
    delay_mode = config_z['delay']['mode'].lower()
    delay_value = str(config_z['delay']['value'])

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

def write_script(dir_path: Path) -> None:
    ''' This function implements the main steps of the application

        Parameters:
                - dir_path: relative path to config directory. The directory contains
                the config.yml, db file and the script template
        
        Synopsis:
            This function does the following:
                - Load configuration from yaml
                - Get commands from log into ordered list
                - Build write dictonary - symbols to be replaces in the template script
                - Open template and write file + commands to string
                - Write string into output file
    '''

    start = datetime.now()

    # Load yaml config from data folder and paths
    config, db_path, srpt_path = load_config(dir_path)

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
    output_file = f"{dir_path}/script-{start.strftime("%d.%m.%Y-%H.%M.%S")}{srpt_path.suffix}"
    with open(output_file, "a") as f:
        f.write(result)
        print(f'Saved script to {output_file}')
        f.close()
    
    end = datetime.now()
    print(f"Elapsed time: {end-start}")

if __name__ == "__main__":

    # Build path
    rel_path = Path("data/")
    if not Path("data/config.yml").exists():
        rel_path = Path("example_data/")
        print("Data directory does not exist. Using example data.")

    write_script(rel_path)
