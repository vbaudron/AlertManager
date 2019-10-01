from model.utils import TableToGenerate
from model.alert import my_sql


def __get_query():
    tables = TableToGenerate.show_tables_request()
    if not tables:
        return None
    print(tables)

    format_param = ", ".join([t for t in tables])

    query = "DROP TABLES {}".format(format_param)
    print(query)
    return query

def __drop_all_tables():
    # NOT BIND
    query = __get_query()
    if not query:
        return
    try:
        my_sql.execute_and_close(query=query)
    except:
        print("exception found")
        query = __get_query()
        my_sql.execute_and_close(query=query)



if __name__ == '__main__':
    __drop_all_tables()
