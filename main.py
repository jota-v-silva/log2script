import sqlite3
import yaml
import re
from itertools import tee, islice, chain
from string import Template
from datetime import datetime
from pathlib import Path

class DataBase:
    def __init__(self, database_file):
        try:
            self.conn = sqlite3.connect(database_file)
            self.cursor = self.conn.cursor()
            print("Successfully connected to the database.")
        except sqlite3.Error as e:
            print("Error connecting to the database:", e)
    
    def __del__(self):
        self.cursor.close()
        self.conn.close()
        print("Database connection closed.")

    def query(self, query):
        return self.cursor.execute(query).fetchall()

def load_config():
    try:
        with open(f"config.yml", "r") as yamlfile:
            config = yaml.load(yamlfile, Loader=yaml.FullLoader)
            return config
    except Exception as e:
        print(f"Unable to load file: \n {e}")

def get_raw_cmds(query_res, regex, script_tpl):
    ''' Gets the query results in the form of a list of tuples, applies the regex to the message
        and writes the corresponding script lines into tupple
    '''
    q_lines = []
    
    # for queries that have multiple occurances
    for entry in query_res:
        id = entry[0]
        time = entry[1]
        msg = entry[3]

        if regex:
            m = re.search(regex, msg)
            if m:
                q_lines.append([id, time, script_tpl.replace('<ARG>', m.group(0))])

    return q_lines

def previous_and_next(some_iterable):
    prevs, items = tee(some_iterable, 2)
    prevs = chain([None], prevs)
    return zip(prevs, items)

def get_clean_cmds(yaml):

    # Get configuration
    db_path = yaml[0]['config']['database']['path']
    delay_mode = yaml[0]['config']['delay']['mode'].lower()
    delay_value = str(yaml[0]['config']['delay']['value'])

    # Load database
    db = DataBase(db_path)
    
    # Get all script cmds
    script_cmds = []
    for q in yaml[1:]:
        query = q['query']
        script_cmds.extend(
            get_raw_cmds(
                db.query(query['sql']),
                query['regex'],
                query['script'])
            )

    # Sort cmds by Id - ensure cmd order is respected
    script_cmds.sort(key=lambda tup: tup[0])

    # Adds delays
    i = 0
    for prev, curr in previous_and_next(script_cmds):
        if prev:
            delay = str(round(curr[1]-prev[1])) if (delay_mode == 'inherited') else delay_value
            script_cmds[i][2] = curr[2].replace('<DELAY>', delay).strip()
        else:
            script_cmds[i][2] = curr[2].replace('<DELAY>', '0').strip()
        i += 1
    
    # Keep script lines only
    i = 0
    for cmd in script_cmds:
        script_cmds[i] = cmd[2]
        i +=1

    return script_cmds

def write_script():

    start = datetime.now()
    yaml = load_config()
    db_path = yaml[0]['config']['database']['path']
    script_tlp_path = Path(yaml[0]['config']['template']['path'])
    script_cmds = get_clean_cmds(yaml)

    # Write replacer dictonary
    d = {
        'date': f'Generated on: {start.strftime("%d/%m/%Y %H:%M:%S")}',
        'db_file': f'Generated from: {db_path}',
        'cmd_list': '\n\n'.join(script_cmds)
    }

    with open(script_tlp_path, 'r') as f:
        src = Template(f.read())
        result = src.substitute(d)
        f.close()
        print(f'Generated script: \n{result}')
    
    output_file = f"script-{start.strftime("%d.%m.%Y-%H.%M.%S")}{script_tlp_path.suffix}"
    with open(output_file, "a") as f:
        f.write(result)
        print(f'Saved script to {output_file}')
        f.close()
    
    end = datetime.now()
    print(f"Elapsed time: {end-start}")

if __name__ == "__main__":
    write_script()
