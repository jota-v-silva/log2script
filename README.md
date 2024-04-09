# log2script

Log2Script is a straightforward utility designed to parse application logs and generate scripts from them. Its primary function is to produce a debug script based on the content of the application log. Currently, it exclusively handles logs in the SQLite format (i.e. *.db files), but it's versatile enough to generate debug scripts in any scripting language.

This tool has found application in two main scenarios:
* [SIMULUS 10/11](https://sim.space-codev.org/)-based spacecraft simulators: Log2Script parses all telecommands and script interactions, compiling them into a Groovy script. This output script is used to replicate complex simulation scenarios.

* Flask applications: For Flask-based applications, Log2Script parses all incoming requests, assembling them into a Python script. This script can then be used to reconstruct intricate sequences of requests.

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
If you don't provide any data, the tool will generate a script from the `example_data`.

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
The `config.yaml` allows for the definition of multiple "query" structures. This section allows you to define what needs to be parsed from the log and be written into the debug script:

```yaml
- query:
    description: "Identifies TC processed successfuly by the TcDecoder and writes command to inject TC directly"
    sql: >
        SELECT rowId, simulationTime, message 
        FROM LOG_MESSAGES WHERE senderName LIKE '%TcDecoder%' AND
        message LIKE '%TC segment received%'
    regex: '(?<=\breceived: \s).*'
    script: |
        Scheduler.SimTimeWait(<DELAY>);
        TcDecoder.InjectSegment("<ARG>");
```
The `sql` entry is the SQLite query to the log.db. Then per each line in the log matching the query, the Log2Script will run the regex and populate the `<ARG>` value in the script section. The `<DELAY>` is computed from the log message time stamp w.r.t the previous message.

The query return parameters need to be returned in a specific order for the parser to work: `rowId`, `time`, `message`.


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
