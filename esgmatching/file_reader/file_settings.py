""" Base class allows to create an object that reflects the content of a json used for settings """

from esgmatching.exceptions import exceptions_settings
from esgmatching.file_reader import file_utils


class JsonSettings:
    """
        This base class provides the infrastructure needed to reflect the content of a json file used
            to describe datasources and its matching policies.

        Attributes: (see DbMatcher)
            file_path (str): filename and path or just path from json settings
            file_extension_pattern (str): an extension patter, such as *.csv to filter files by type in a folder
            filename_pattern (str): filename pattern from json settings (used when file_path is a directory and
                the system has to capture the most recent file that follows the filename pattern.
            file_encoding (str): file encoding from json settings
            file_separator (str): file separator from json settings
            datasource_name (str): name of the datasource
            datasource_table_name (str): name of the equivalent database table
            datasource_create_table (bool): indicates if the table needs to be created (True or False)
            datasource_if_table_exists (str): indicates what to do if the tables exists (drop or clean)
            datasource_primary_keys (list): list with the names of the primary keys
            datasource_attributes  (dict): dictionary with the attribute names. The dict keys are the names of the
                attributes in the file header. The dict items are the names of the attributes in the equivalente
                database table.
            matching_role (str): indicates the role of the datasource in a matching process (target or referential)
            matching_alias (dict): dictionary with alias to some of the datasource attributes. The dict keys are the
                alias names, while the items are the names of the attributes in the equivalente database table.
            map_to_matching (dict): dictionary that maps some datasource attributes to attributes in the matching
                table. The dict keys are are the attribute names in the matching table, while the items are the
                attribute names in the database table for the datasource.
            map_indirect_matching (dict): dictionary with the association between target and referential columns that
                need to be switched when performing the indirect matching.
            matching_policy (dict): dictionary that describe the matching policies.
    """

    def __init__(self, json_settings):
        # File processing settings
        self.file_path = ''
        self.file_extension_pattern = ''
        self.filename_pattern = ''
        self.file_encoding = 'utf-8'
        self.file_separator = ';'

        # Data source settings
        self.datasource_name = 'unknown'
        self.datasource_table_name = 'unknown'
        self.datasource_create_table = True
        self.datasource_if_table_exists = 'drop'
        self.datasource_primary_keys = None
        self.datasource_attributes = None
        self.matching_role = 'target'
        self.matching_id = ''
        self.matching_alias = None
        self.map_to_matching = None
        self.map_indirect_matching = None

        # Matching policies
        self.matching_policy = None

        # Check if the settings file exists
        if file_utils.file_exists(json_settings):
            self._filename_settings = json_settings
        else:
            raise exceptions_settings.FileSettingsDoesNotExist

        # Check if the settings file is a json file
        if file_utils.get_extension(self._filename_settings) != '.json':
            raise exceptions_settings.FileSettingsIsNotAJsonFile

        # Read settings from json file
        dict_json = file_utils.read_json_file(self._filename_settings)
        self._set_file_processing_settings(dict_json)
        self._set_data_source_settings(dict_json)
        self._set_matching_policy_settings(dict_json)

    def _set_file_processing_settings(self, settings_json: dict):
        """
            Private class method used to load file processing settings from the json file to its
                correspondent object variables.

            Parameters:
                settings_json (dict) : the dictionary read from a json file

            Returns:
                No return value.

            Raises:
                No exception is raised.
        """
        # Read the [file_processing] section of the json file
        if 'file_processing' in settings_json:
            sub_dict = settings_json['file_processing']
            if 'file_path' in sub_dict:
                self.file_path = sub_dict['file_path']
            if 'file_extension_pattern' in sub_dict:
                self.file_extension_pattern = sub_dict['file_extension_pattern']
            if 'filename_pattern' in sub_dict:
                self.file_path = sub_dict['file_path']
            if 'encoding' in sub_dict:
                self.file_encoding = sub_dict['encoding']
            if 'separator' in sub_dict:
                self.file_separator = sub_dict['separator']

    def _set_data_source_settings(self, settings_json: dict):
        """
            Private class method used to load data source settings from the json file to its
                correspondent object variables.

            Parameters:
                settings_json (dict) : the dictionary read from a json file

            Returns:
                No return value.

            Raises:
                exceptions_settings.DataSourceSettingsNotDefined when datasource settings is not defined in json
                exceptions_settings.IfTableExistsNotRecognized when wrong values are defined in json
                exceptions_settings.MatchingRoleNotRecognized when wrong values are defined in json
                exceptions_settings.AliasMatchingNotDefined when aliases are not defined
                exceptions_settings.FieldsMappingToMatchingTableNotDefined when attribute mapping is not defined
                exceptions_settings.FieldsMappingToNoMatchingTableNotDefined when attribute mapping is not defined
        """
        # Read the [data_source] section of the json file
        if 'data_source' in settings_json:
            sub_dict = settings_json['data_source']
            if 'name' in sub_dict:
                self.datasource_name = sub_dict['name']
            if 'table_name' in sub_dict:
                self.datasource_table_name = sub_dict['table_name']
            if 'create_table' in sub_dict:
                self.datasource_create_table = eval(sub_dict['create_table'])
            if 'if_table_exists' in sub_dict:
                value_dict = sub_dict['if_table_exists']
                if value_dict != 'drop' and value_dict != 'clean':
                    raise exceptions_settings.IfTableExistsNotRecognized
                self.datasource_if_table_exists = value_dict
            if 'primary_keys' in sub_dict:
                value_dict = list(sub_dict['primary_keys'])
                if len(value_dict) > 0:
                    self.datasource_primary_keys = value_dict
            if 'attributes' in sub_dict:
                value_dict = sub_dict['attributes']
                if len(value_dict) > 0:
                    self.datasource_attributes = value_dict
            if 'matching_role' in sub_dict:
                value_dict = sub_dict['matching_role']
                if value_dict not in ['referential', 'target', 'matching', 'no-matching']:
                    raise exceptions_settings.MatchingRoleNotRecognized
                self.matching_role = value_dict
            if 'matching_id' in sub_dict:
                self.matching_id = sub_dict['matching_id']
            if 'matching_alias' in sub_dict:
                value_dict = dict(sub_dict['matching_alias'])
                if len(value_dict) > 0:
                    self.matching_alias = value_dict
                else:
                    raise exceptions_settings.AliasMatchingNotDefined
            if 'map_to_matching' in sub_dict:
                value_dict = dict(sub_dict['map_to_matching'])
                if len(value_dict) > 0:
                    self.map_to_matching = value_dict
                else:
                    raise exceptions_settings.FieldsMappingToMatchingTableNotDefined
            if 'map_indirect_matching' in sub_dict:
                value_dict = dict(sub_dict['map_indirect_matching'])
                if len(value_dict) > 0:
                    self.map_indirect_matching = value_dict
                else:
                    raise exceptions_settings.FieldsMappingToMatchingTableNotDefined
        else:
            raise exceptions_settings.DataSourceSettingsNotDefined

    def _set_matching_policy_settings(self, settings_json: dict):
        """
            Private class method used to load matching policy settings from the json file to its
                correspondent object variable.

            Parameters:
                settings_json (dict) : the dictionary read from a json file

            Returns:
                No return value.

            Raises:
                exceptions_settings.MatchingPolicyEmpty when matching policy is empty
                exceptions_settings.ReferentialIsMissingInMatchingPolicy when matching policy is incorrect
                exceptions_settings.MatchingSourceIsMissingInMatchingPolicy when matching policy is incorrect
                exceptions_settings.NoMatchingSourceIsMissingInMatchingPolicy when matching policy is incorrect
                exceptions_settings.DfmRulesEmptyInMatchingPolicy when matching policy is incorrect
                exceptions_settings.DrmRulesEmptyInMatchingPolicy when matching policy is incorrect
                exceptions_settings.IfmRulesEmptyInMatchingPolicy when matching policy is incorrect
        """
        # Read the [file_processing] section of the json file
        if 'matching_policy' in settings_json:
            sub_dict = settings_json['matching_policy']
            if len(sub_dict) == 0:
                raise exceptions_settings.MatchingPolicyEmpty
            for policy_name in sub_dict:
                policy_dict = sub_dict[policy_name]
                if 'dfm' in policy_dict:
                    rules_dict = policy_dict['dfm']
                    if len(rules_dict) == 0:
                        raise exceptions_settings.DfmRulesEmptyInMatchingPolicy
                if 'drm' in policy_dict:
                    rules_dict = policy_dict['drm']
                    if len(rules_dict) == 0:
                        raise exceptions_settings.DrmRulesEmptyInMatchingPolicy
                if 'ifm' in policy_dict:
                    rules_dict = policy_dict['ifm']
                    if len(rules_dict) == 0:
                        raise exceptions_settings.IfmRulesEmptyInMatchingPolicy
            self.matching_policy = sub_dict