import sys
import os

# dir_path = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(os.path.abspath(dir_path))

from scripts.serverside.serverside_table import ServerSideTable
from scripts.serverside.table_schemas import SERVERSIDE_TABLE_COLUMNS


class TableBuilder(object):
    def collect_data_serverside(self, request, data):
        columns = SERVERSIDE_TABLE_COLUMNS
        return ServerSideTable(request, data, columns).output_result()