import sqlite3

class Sqlite:
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