    # PRECONDITION -----------------------------------------------------------------------------------------------------
    def establish_preconditions(self, pool_name):
        """
        This functions holds the code which prepares the environment for the test.
        :param pool_name: str
            Name of the datapool for TM/TCs in the database
        :return: bool
            True if the preconditions are fulfilled
        """
        #testing_logger.cmd_log_handler(__name__)
        success = False
        logger.info('establishing preconditions started')

        $testpreconentry

        logger.info('establishing preconditions finished')
        report.write_precondition_outcome(success)
        return success

    # INITIALIZE every step --------------------------------------------------------------------------------------------
    def begin_steps(self, pool_name, param):
        """
        This functions initializes every step, the step itself is done in the step functions
        :param pool_name: str
            Name of the datapool for TM/TCs in the database
        :param param: list
            Includes the parameters of the step
        :return: step_start_cuc: time
            Time of the last incomming package before the step is started/ used as time of step start
        :return: summary: report.StepSummary class object
            Containes a summary of the test
        :return: tc_id:
        """
        testing_logger.cmd_log_handler(__name__)
        step_start_cuc = cfl.get_last_pckt_time(pool_name=pool_name, string=False)
        report.command_step_begin(step_param=param, script_version=self.version(), pool_name=pool_name,
                                  step_start_cuc=step_start_cuc)

        summary = report.StepSummary(step_number=param['step_no'])
        tc_id = None
        return step_start_cuc, summary, tc_id
