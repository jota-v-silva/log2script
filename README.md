# Log2Script

A very simple tool that parses an application log and writes a script from it. The main purpose of Log2Script is to generate a debug script from the application log. Currently it only supports logs written in the SQL format (i.e. *.db files), but it supports the generation of debug scripts in any scripting laguange.

## Quick start
Copy your config data (`config.yml`, `*.db` and `template.`) to your home directory and run:

```bash
docker-compose up --build log2script
```

If you would like to modfiy the data path, update the compose.yaml:

```yaml
    volumes:
      - <PATH_TO_DATA>:/data # Modify the mount path as needed. Destination path is always /data
```

## How it works
The file `config.yaml` defines the application specific details. The config struct defines the general info to allow the Log2Script to work:

``` yaml
- config: 
    delay: # defines time interval between script entries
        mode: default # inherited or default
        value: 1000 # default delays - 1sec
    template: # the script template
        path: template.py # relative path to template
        time_base: milliseconds # not used anywhere, just for reference
    database:
        path: test_log.db # relative path to template
        table_name: LOG_MESSAGES
        mandatory_fields: # The fields that need to exist in the table schema
            - messageId
            - time
            - level
            - message
```
The `config.yaml` allows for the definition of multiple "query" structures. This is the config section that allows you to define what needs to be parsed from the log and written into the debug script:

```yaml
- query:
    description: "Get input value"
    seq: NA
    sql: >
        SELECT messageId, time, message
        FROM LOG_MESSAGES WHERE message LIKE '%Input value changed to%'
    regex: '\s(\S+)$'
    script: |
        time.sleep(<DELAY>)
        app.set_input(<ARG>)
```
The `sql` entry is the SQLite query to the log.db. Then per each line in the log matching the query, the Log2Script will run the regex and populate the `<ARG>` value in the script scetion. The `<DELAY>` is computed from the log message time stamp w.r.t the previous message.

The script entries are written into script template using the key words `date`, `db_file` and `cmd_list`:
```groovy
// --------------------------------------------------------------------------------
//
// Groovy template file
// 
// $date
// $db_file
//
// --------------------------------------------------------------------------------

// Import section

// Generated section
$cmd_list
```

## Todos
* Add clean data example
* Add support for multiple regex/args - regex[1] -> ARG1, etc
