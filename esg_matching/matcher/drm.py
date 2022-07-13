""" Base class allows to create a matcher that performs direct residual matching on a database """

from esg_matching.matcher.db_matcher import DbMatcher
from esg_matching.engine.connectors.base_connector import DbConnector
from esg_matching.matcher.policy import MatchingPolicy
from esg_matching.exceptions import exceptions_matching_policy


class DbMatcherDrm(DbMatcher):
    """
        This base class provides the infrastructure needed to perform direct residual matching in a database.

        Attributes: (see DbMatcher)
            _matching_type (str): indicates the type of matching to be performed. It can be:
                'direct_residual_matching': (drm) performs matching between a referential datasource and the records
                                        in the no-matching table. It is called 'residual' because it is performed
                                        on the entries that were not matched after a dfm was executed. It  also
                                        operates on join condition rules. But, this time the joins are between a
                                        referential datasource and the no-matching entries.
    """

    def __init__(self, db_connector: DbConnector):
        """
            Constructor method.

            Parameters:
                db_connector (DbConnector): database connectors

            Returns:
                DbMatcherDrm (object)

            Raises:
                No exception is raised.
        """
        super().__init__(db_connector)
        self._matching_type = 'drm'
        self._literal_matching_type = 'direct'
        self._literal_matching_scope = 'residual'

    def _can_matcher_be_used(self, policy: MatchingPolicy):
        """
            Private class method used to check if the policy can be applied to the instanciated matcher.
            In the case of DFM, it checks if the policy has at least one rule for 'direct_residual_matching'.

            Parameters:
                policy (MatchingPolicy) : the matching policy contains the description of the matching rules.

            Returns:
                True if the matcher is described as a matching process in the given policy, or
                False, otherwise.

            Raises:
                No exception is raised.
        """
        # Check if the policy contains rules to perform the direct residual matching
        if not policy.has_rule_type(self._matching_type):
            raise exceptions_matching_policy.DirectResidualMatchingNotInPolicy

    def _get_conditions(self, attribute_rules):
        """
            Private class method that builds the join and where conditions that will be used to form the matching and
                the no-matching sql statements. For DRM, the join clause is built between the target and no-matching.
                The alias_attributes is mapped to the target and no-matching datasource as build the equality condition
                for the join. The where condition is used only to build the no-matching table.

            Parameters:
                attribute_rules (list) : a list of attribute aliases that represent the names of table attributes
                    of the datasources participating on a matching/nno-matching process.

            Returns:
                join_condition (sqlalchemy.sql.expression): the join condition
                where_condition (sqlalchemy.sql.expression): the where condition

            Raises:
                No exception is raised.
        """
        # Build the condition for the join and where clauses
        join_condition = None
        for alias_attribute in attribute_rules:
            tgt_col_name = self._tgt_source.get_matching_attribute_by_alias(alias_attribute)
            left_db_col = self._no_matching_source.get_table_column(tgt_col_name)
            right_db_col = self._ref_source.get_table_column_by_alias(alias_attribute)
            self._join_condition_builder = self._join_condition_builder.create_condition()\
                .equal_cols(left_db_col, right_db_col)
            if join_condition is None:
                join_condition = self._join_condition_builder.get_condition()
            else:
                self._join_condition_builder = self._join_condition_builder.and_condition(join_condition)
                join_condition = self._join_condition_builder.get_condition()
        tgt_name = self._tgt_source.name
        tgt_db_name = self._no_matching_source.get_table_column('tgt_name')
        self._where_condition_builder = self._where_condition_builder.create_condition()
        self._where_condition_builder = self._where_condition_builder.equal_value(tgt_db_name, tgt_name)
        where_condition = self._where_condition_builder.get_condition()
        return join_condition, where_condition

    def _get_cols_match(self, rule_name):
        """
            Private class method that builds a list with the columns of the select statement that computes positive
            matches. These columns are a combination of the columns in the target and referential data sources
            that are mapped to the matching database table. Also, literal columns are added as to include columns
            that describe each row of the positive matching.

            Parameters:
                rule_name (str) : the name of the matching rule is passed as parameter because this method calls
                    _get_literal_cols_match() method.

            Returns:
                select_db_cols (list): list of sqlalchemy.sql.schema.Column objects with all the columns used in the
                    select statement that computes positive matches. Overall, select_db_cols is the sum of literal
                     columns, columns from the target datasource and columns from the referential datasource.
                select_name_cols (list): list with the names of all select_db_cols.

            Raises:
                No exception is raised.
        """
        literal_db_cols, literal_name_cols = self._get_literal_cols_match(rule_name)
        no_match_name_cols = self._tgt_source.get_name_cols_mapped_to_matching()
        no_match_db_cols = self._no_matching_source.get_db_cols_with_same_name(no_match_name_cols)
        ref_db_cols = self._ref_source.get_db_cols_mapped_to_matching()
        ref_name_cols = self._ref_source.get_name_cols_mapped_to_matching()
        select_db_cols = literal_db_cols + no_match_db_cols + ref_db_cols
        select_name_cols = literal_name_cols + no_match_name_cols + ref_name_cols
        return select_db_cols, select_name_cols

    def execute_matching(self):
        """
            Class method that executes the direct full matching (DFM), a join between referential and target tables.

            Parameters:
                No parameters required.

            Returns:
                No return value.

            Raises:
                No exception is raised.
        """
        # Open a session if one does not exist already
        # if not self._db_connector.has_session_open():
        #    self._db_connector.create_session()
        for rule_key in self._matching_rules:
            # ------ MATCHING PROCESS ------
            # Process positive matchings: this is basically an INSERT into the MATCHING_TABLE taken values
            # from a SELECT JOIN beetween the TARGET_TABLE and REFERENTIAL_TABLE
            # Get the columns of the INSERT...SELECT that computes the positive results (matchings)
            select_db_cols, select_name_cols = self._get_cols_match(rule_key)

            # Get the attribute names that will form the join condition (for matching) and the where_condition
            # used in the no-matching. The attributes are alias mapped to the real attribute names in the target
            # and the referencial datasources.
            join_condition, where_condition = self._get_conditions(self._matching_rules[rule_key])

            # Build the select statement
            self._select_builder = self._select_builder.create_select(select_db_cols)
            self._select_builder = self._select_builder.from_table(self._no_matching_table)
            self._select_builder = self._select_builder.join_table(self._ref_table).join_on(join_condition)
            self._select_builder = self._select_builder.where_condition(where_condition)
            select_stm = self._select_builder.build_statement()

            # Get the metadata columns of the matching table
            # The columns of the matching table must be the same, in the same order as the ones in the
            # select statement. Therefore, the column names of the select is sent by paramenter.
            matching_db_cols = self._matching_source.get_db_cols_with_same_name(select_name_cols)
            self._dml_manager.insert_into_from_select(self._matching_table, matching_db_cols, select_stm)

            # ------ NO-MATCHING PROCESS ------
            # DELETE MATCHING RESULTS FROM NO-MATCHING TABLE
            # Build the select statement
            col_matching_id_name = self._no_matching_source.matching_id
            col_matching_id_db = self._no_matching_source.get_table_column(col_matching_id_name)
            self._select_builder = self._select_builder.create_select(col_matching_id_db)\
                .from_table(self._no_matching_table).join_table(self._ref_table).join_on(join_condition)\
                .where_condition(where_condition)
            select_stm = self._select_builder.build_statement()
            self._delete_builder = self._delete_builder.create_delete().from_table(self._no_matching_table)\
                .where_in_condition(col_matching_id_db, select_stm)
            delete_stm = self._delete_builder.build_statement()
            self._dml_manager.delete_data(delete_stm)

            # Commit changes
            # self._db_connector.commit_changes()
        # Close the session
        # self._db_connector.close_session()