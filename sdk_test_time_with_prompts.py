import os
import paramiko
import pymysql
import pandas as pd
import base64
import glob
import re
import json
from datetime import datetime
from pathlib import Path
from module_chaining.module_chaining import ModuleManager

class Constants:
    OUTPUT_DIR = '/home/modules/eData/userOutputFiles/'
    NO_OF_TRIES = 3
    PORT = 22
    REMOTE_VM_DETAILS = "engui_vm_details"
    REMOTE_FILE_DIR = "log_file_directory"
    IP = "ip"
    USER = "user"
    PASSWORD = "pwd"
    TARGET_DIR_PATH = "/home/modules/logs/system_performance"
    JSON_FILE_PATH = '/home/modules/eData/userInputFiles/crontablog.json'
    CONFIG_PATH = '/home/modules/eData/userInputFiles/SFR_KPI_REPORTS/custom_kpi_module/system_performance_config.ini'
    SEARCH_STRING = "search_string"
    STRING_TO_SEARCH_IN_LOG = "string_to_search_log_file"
    STRING_PER_KPI = "string_to_search_per_kpi"
    PLAN_PREP_COMPLETION_ANR_5G = "plan_preparation_phase_completion_status_ANR_5G"
    PLAN_PREP_COMPLETION_ANR_3G = "plan_preparation_phase_completion_status_ANR_3G"
    PLAN_PREP_COMPLETION_ANR_2G = "plan_preparation_phase_completion_status_ANR_2G"
    PLAN_PREP_COMPLETION_ANR_4G_IRAT = "plan_preparation_phase_completion_status_ANR_4G_IRAT"
    PLAN_PREP_COMPLETION_ANR_4G_CL = "plan_preparation_phase_completion_status_ANR_4G_CL"
    PLAN_PREP_START_4G = "4G_plan_preparation_start_ANR_5G"
    PLAN_PREP_START_5G = "5G_plan_preparation_start_ANR_5G"
    PLAN_PREP_END_ANR_5G = "Plan_preparation_end_ANR_5G"
    PLAN_PREP_END_ANR_5G_5G = 'Plan_preparation_end_ANR_5G_5G'
    PLAN_PREP_END_ANR_3G = "Plan_preparation_end_ANR_3G"
    PLAN_PREP_END_ANR_2G = "Plan_preparation_end_ANR_2G"
    PLAN_PREP_END_ANR_4G_IRAT = "Plan_preparation_end_ANR_4G_IRAT"
    PLAN_PREP_END_ANR_4G_CL = "Plan_preparation_end_ANR_4G_CL"
    PLAN_PREP_END_ANR_4G_BL = "Plan_preparation_end_ANR_4G_BL"
    PROVISION_STATUS_5G = "5G Provisioning Duration"
    PROVISION_STATUS_4G = "4G Provisioning Duration"
    MODULE_INSTANCE_START_ANR_3G = "Module_Instance_start_ANR_3G"
    MODULE_INSTANCE_START_ANR_2G = "Module_Instance_start_ANR_2G"
    MODULE_INSTANCE_START_ANR_4G_IRAT = "Module_Instance_start_ANR_4G_IRAT"
    MODULE_INSTANCE_START_ANR_4G_CL = "Module_Instance_start_ANR_4G_CL"
    MODULE_INSTANCE_START_ANR_4G_BL = "Module_Instance_start_ANR_4G_BL"
    MODULE_INSTANCE_END_ANR_5G = "Module_Instance_end_ANR_5G"
    MODULE_INSTANCE_END_ANR_3G = "Module_Instance_end_ANR_3G"
    MODULE_INSTANCE_END_ANR_2G = "Module_Instance_end_ANR_2G"
    MODULE_INSTANCE_END_ANR_4G_IRAT = "Module_Instance_end_ANR_4G_IRAT"
    MODULE_INSTANCE_END_ANR_4G_CL = "Module_Instance_end_ANR_4G_CL"
    MODULE_INSTANCE_END_ANR_4G_BL = "Module_Instance_end_ANR_4G_BL"
    PROVISION_END_ANR_5G = "Provisioning_end_ANR_5G"
    PROVISION_END_ANR_3G = "Provisioning_end_ANR_3G"
    PROVISION_END_ANR_2G = "Provisioning_end_ANR_2G"
    PROVISION_END_ANR_4G_IRAT = "Provisioning_end_ANR_4G_IRAT"
    PROVISION_END_ANR_4G_CL = "Provisioning_end_ANR_4G_CL"
    PROVISION_END_ANR_4G_BL = "Provisioning_end_ANR_4G_BL"
    ANR_2G_3G_4G_MODULE_NAMES = ["ANR_2G", "ANR_3G", "ANR_4G_IRAT"]
    CALC_DURATION = "Calculation Duration"

def getjsondata(jsonfile):
    """
    method to read the json file and return the jason data
    :param jsonfile: json File
    :return: returns json data
    """
    # Opening JSON file
    f = open(jsonfile, )

    # returns JSON object as
    # a dictionary
    data = json.load(f)

    # Closing file
    f.close()

    return data

def get_config_json(conf_file):
    """
    Method to read the configuration json file
    :param script_data: standard input parameter
    :param cmlogger: logger
    :param module_config_name: Module Configuration name
    :return: returns the read configuration data
    """
    input_path = conf_file
    if not input_path:
        print("Configuration file - {} not found .".format(input_path))
        raise Exception
    try:
        module_config_data = getjsondata(input_path)
    except Exception as error:
        print("Exception found while reading the configuration file - {} .".format(error))
        raise Exception("Exception caught : {}".format(error))

    return module_config_data

class SFTPHandler:

    def __init__(self, config_data):
        self.config_data = config_data

    def transfer_file_to_server(self, file_directory, target_directory, module_instance_id,
                                server_details):
        """
        Methid to connect to GUI server and fetch the log files
        :param file_directory: Log path
        :param target_directory: target directory to copy files
        :param module_instance_id: module instance id
        :param anr_module_name: module name
        :param user_name: user name
        :param server_details: GUI server details to fetch the logs
        :return: returns the list of files
        """
        transport, sftp_client, file_name_list = None, None, None
        try:
            print("file_directory: ", file_directory)
            print("target_directory: ", target_directory)
            list_of_files = []
            sftp_pass_word = decode_password(server_details[2])
            transport, sftp_client = self.create_sftp_client(server_details[0], server_details[1], sftp_pass_word)
            if transport and sftp_client:
                file_name_list = self.get_latest_remote_file(sftp_client, file_directory, module_instance_id)
                if not os.path.exists(target_directory):
                    os.makedirs(target_directory)
                for each_file in file_name_list:
                    sftp_client.get(os.path.join(file_directory, each_file),
                                    os.path.join(target_directory, each_file))
                    list_of_files.append(os.path.join(target_directory, each_file))
                    print("Transferring {0} from server ".format(each_file))
                print("list of files are - {}".format(list_of_files))
                return list_of_files
            else:
                print("Exception caught while connecting to GUI server")
                raise Exception("Failed to establish connection to Server {}")
        except Exception as e:
            print("Failed transferring files to Server {}".format(e))
            raise Exception("Failed to transfer the files : {}".format(e))
        finally:
            print("Closing the resource of sftp connection")
            try:
                if transport:
                    if transport.is_active():
                        sftp_client.close()
                        transport.close()
                print("Closing the resource of sftp connection succeeded")
            except Exception as exc:
                print("Exception while closing the sftp resources, {}".format(exc))
                raise Exception("Exception while closing the sftp resources, {}".format(exc))

    def create_sftp_client(self, ip, username, password=None):
        """
        create ftp connection to remote server
        :param ip: GUI server IP
        :param username: root user
        :param password: root user password
        :return: returns details of sftp client connection tuple
        """
        if ip and username:
            for iteration in range(0, Constants.NO_OF_TRIES):
                try:
                    transport = paramiko.Transport((ip, Constants.PORT))
                    if password:
                        print(
                            "Connecting to server using password")
                        transport.connect(username=username, password=password)
                    else:
                        print("Connecting to server using RSA key")
                        transport.connect(username=username,
                                          pkey=paramiko.RSAKey.from_private_key_file(
                                              os.path.expanduser('~/.ssh/id_rsa')))

                    return transport, paramiko.SFTPClient.from_transport(transport)
                except Exception as e:
                    print("Try {}: FTP Connection Failed to Server {}, with error : {}".
                                     format(iteration, ip, e))
        else:
            print("Cannot connect to remote server, either ipAddress or username is missing.")

        return None, None

    def get_latest_remote_file(self, sftp_client, path, module_instance_id):
        """
        Method to get the filtered log files
        :param sftp_client: SFTP
        :param path: log file path
        :param module_instance_id: module instance id
        :param anr_module_name: module name
        :param user_name: user name
        :return: returns the list of log files
        """
        try:
            sftp_client.chdir(path)
            filtered_file_names = []
            print("Fetching the file for the instance {}".format(module_instance_id))
            # for file_attr in sftp_client.listdir_attr():
            for file_attr in sorted(sftp_client.listdir_attr(), key=lambda f: f.st_mtime):
                # if file_attr.filename.startswith(anr_module_name + '_' + user_name + '_'):
                if file_attr.filename.startswith(module_instance_id):
                    # current_time = time.time()
                    creation_time = file_attr.st_mtime
                    readable_time = datetime.fromtimestamp(creation_time)
                    # if (current_time - creation_time) // (24 * 3600) < 1:
                    filtered_file_names.append(file_attr.filename)

            print("Log files for the instance {} ".format(filtered_file_names))
            if not filtered_file_names:
                print(
                    "No Log Files identified for the module {0} from path {1}, hence stopping the execution".
                    format(module_instance_id, path))
                raise Exception("No log files found for the module {} from path {}".
                                format(module_instance_id, path))
            return filtered_file_names

        except IOError as error:
            print(
                "Exception caught while fetching the log files from path {}, exception {}".format(path, error))
            raise Exception("Exception while fetching the log files".format(error))


def decode_password(auth_pass):
    """
    Method to decode the give password
    :param auth_pass: encoded password
    :param logger: logger
    :return: returns decoded password
    """
    try:
        auth_pass_decoded = base64.b64decode(auth_pass).decode("utf-8")
        return str(auth_pass_decoded).replace('\n', '')
    except Exception as e:
        print("Provide password in Base64 with Padding encoded format")
        raise e

def read_log_return_dataframe(log_filenames):
    """
    Method to get the file content
    :param log_filenames: list of files fetched for the module instance
    :return: returns the dataframe of file content
    """
    global already_read_files
    files_data = []
    for file_name in log_filenames:
        # Skip files that have already been read
        if file_name in already_read_files:
            print(f"Skipping already read file: {file_name}")
            continue
        with open(file_name, 'r') as text_file:
            file_text = text_file.read().splitlines()
        df = pd.DataFrame(file_text, columns=["Content"])  # Adding a column name for clarity
        files_data.append(df)
        already_read_files.add(file_name)

    if not files_data:
        raise Exception("No new log files found to read.")

    return pd.concat(files_data, ignore_index=True)


def get_file_names(path, file_name=None):
    """
    Methods gets the latest file from the given path/directory
    :param file_name: name of the file
    :param path: given absolute path
    :return: file names list
    """
    try:
        latest_files_name = []
        if os.path.isdir(path) and os.path.exists(path):
            latest_files = glob.glob(os.path.join(path, file_name))
            if latest_files:
                latest_files.sort(key=os.path.getctime)
                latest_files_name = [os.path.basename(file) for file in latest_files if
                                     not file.__contains__("consolidated")]
            else:
                pass
            return latest_files_name
        else:
            # raise Exception("path not available {} \n".format(path))
            return latest_files_name
    except IOError as error:
        raise error

def return_params(data):
    """
    Method to return the module name and user name parameter
    :param data: target module instance name
    :return: module_name : target module name
    :return : user_name : target module user name
    """
    data_list = str(data).split("_")
    user_name = ""
    for each_data in data_list:
        if len(each_data) == 8 and not re.search('[a-zA-Z]', each_data):
            date_index = data_list.index(each_data)
            user_name = data_list[date_index - 1]
    module_name = data.split("_" + user_name)[0]
    return module_name, user_name

def generate_data_with_values(log_file_data, config_data):
    """
    Method to generate the log file dataframe with required search
    :param log_file_data: log file dataframe
    :param config_data: config data
    :return: returns the searched dataframe
    """
    log_file_data.columns = ['log_data']

    log_file_data['date_time'] = log_file_data['log_data'].str.extract(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
                                                                       expand=True)
    log_file_data['date_time'].ffill(inplace=True)
    # string_to_search = config_data.get(Constants.STRING_TO_SEARCH_IN_LOG).get(Constants.SEARCH_STRING)
    string_to_search = [*config_data.get(Constants.STRING_PER_KPI).values()]

    log_file_data = get_data(log_file_data, string_to_search)

    return log_file_data

def get_data(file_dataframe, statements_to_search):
    data = file_dataframe[file_dataframe['log_data'].str.contains("|".join(statements_to_search))]
    return data

def get_kpi_data(df, search, index):
    if not search:
        return ''
    if index < len(df[df['log_data'].str.contains(search)]['date_time'].values):
        date_time = df[df['log_data'].str.contains(search)]['date_time'].values[index].__str__()
        if date_time:
            return date_time
        else:
            return ''
    else:
        return ''

def get_status_time_related_2g3g4g_kpi(config_data, data_df, iteration,module_type):
    try:
        if anr_module_name in "ANR_2G":
            search_string_plan_prep_comp = Constants.PLAN_PREP_COMPLETION_ANR_2G
            search_string_plan_prep_end = Constants.PLAN_PREP_END_ANR_2G
            search_string_module_instance_start = Constants.MODULE_INSTANCE_START_ANR_2G
            search_string_module_instance_end = Constants.MODULE_INSTANCE_END_ANR_2G
            search_string_provision_end = Constants.PROVISION_END_ANR_2G
        if anr_module_name in "ANR_3G":
            search_string_plan_prep_comp = Constants.PLAN_PREP_COMPLETION_ANR_3G
            search_string_plan_prep_end = Constants.PLAN_PREP_END_ANR_3G
            search_string_module_instance_start = Constants.MODULE_INSTANCE_START_ANR_3G
            search_string_module_instance_end = Constants.MODULE_INSTANCE_END_ANR_3G
            search_string_provision_end = Constants.PROVISION_END_ANR_3G
        if anr_module_name in "ANR_4G_IRAT":
            search_string_plan_prep_comp = Constants.PLAN_PREP_COMPLETION_ANR_4G_IRAT
            search_string_plan_prep_end = Constants.PLAN_PREP_END_ANR_4G_IRAT
            search_string_module_instance_start = Constants.MODULE_INSTANCE_START_ANR_4G_IRAT
            search_string_module_instance_end = Constants.MODULE_INSTANCE_END_ANR_4G_IRAT
            search_string_provision_end = Constants.PROVISION_END_ANR_4G_IRAT
        if anr_module_name in "ANR_Blacklisting_and_Cleanup_LTE" and module_type == "Blacklisting":
            search_string_plan_prep_comp = Constants.PLAN_PREP_END_ANR_4G_BL
            search_string_plan_prep_end = Constants.PLAN_PREP_END_ANR_4G_BL
            search_string_module_instance_start = Constants.MODULE_INSTANCE_START_ANR_4G_BL
            search_string_module_instance_end = Constants.MODULE_INSTANCE_END_ANR_4G_BL
            search_string_provision_end = Constants.PROVISION_END_ANR_4G_BL
        if anr_module_name in "ANR_Blacklisting_and_Cleanup_LTE" and module_type == "Cleanup":
            search_string_plan_prep_comp = Constants.PLAN_PREP_COMPLETION_ANR_4G_CL
            search_string_plan_prep_end = Constants.PLAN_PREP_END_ANR_4G_CL
            search_string_module_instance_start = Constants.MODULE_INSTANCE_START_ANR_4G_CL
            search_string_module_instance_end = Constants.MODULE_INSTANCE_END_ANR_4G_BL
            search_string_provision_end = Constants.PROVISION_END_ANR_4G_CL

        data_77 = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                               get(search_string_plan_prep_comp), iteration - 1)

        if data_77:
            data_77 = '100%'
        else:
            data_77 = '0%'

        data_78 = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                               get(search_string_module_instance_start), iteration - 1)
        print("for ANR_CL_BL:",data_78)
        data_79 = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                               get(search_string_module_instance_end), iteration - 1)

        data_81 = get_duration(data_79, data_78, Constants.CALC_DURATION)

        data_83 = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                               get(search_string_module_instance_end), iteration - 1)

        data_84 = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                               get(search_string_provision_end), iteration - 1)

        data_85 = get_duration(data_84, data_83, "Provisioning Duration")

        time_kpi_list = [data_77, data_78, data_79, data_81, data_83, data_84, data_85]

        for kpi in range(len(time_kpi_list)):
            if isinstance(time_kpi_list[kpi], str):
                time_kpi_list[kpi] = time_kpi_list[kpi].split(",")

        data_77, data_78, data_79, data_81, data_83, data_84, data_85 = time_kpi_list

        return {'kpi_77':data_77,'kpi_78': data_78,'kpi_79': data_79,
                'kpi_81':data_81,'kpi_83': data_83,'kpi_84': data_84, 'kpi_85': data_85}

    except Exception as exp:
        raise Exception("Exception while calculating the KPIS based on log file {}".format(exp))

def get_status_time_related_5g_kpi(config_data ,data_df, iteration):
    try:
        data_77a = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.PLAN_PREP_COMPLETION_ANR_5G), iteration - 1)
        if data_77a:
            data_77a = '100%'
        else:
            data_77a = '0%'

        data_77b = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.PLAN_PREP_COMPLETION_ANR_5G), iteration - 1)
        if data_77b:
            data_77b = '100%'
        else:
            data_77b = '0%'

        data_78a = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.PLAN_PREP_START_4G), iteration - 1)

        data_78b = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.PLAN_PREP_START_5G), iteration - 1)

        data_79a = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.PLAN_PREP_END_ANR_5G), iteration - 1)

        data_79b = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.PLAN_PREP_END_ANR_5G_5G), iteration - 1)

        data_81a = get_duration(data_79a, data_78a, Constants.CALC_DURATION)

        data_81b = get_duration(data_79b, data_78b, Constants.CALC_DURATION)

        data_83a = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.MODULE_INSTANCE_END_ANR_5G), iteration - 1)

        data_83b = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.MODULE_INSTANCE_END_ANR_5G), iteration - 1)

        data_84a = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.PROVISION_END_ANR_5G), iteration - 1)

        data_84b = get_kpi_data(data_df, config_data.get(Constants.STRING_PER_KPI).
                                get(Constants.PROVISION_END_ANR_5G), iteration - 1)

        data_85a = get_duration(data_84a, data_83a, Constants.PROVISION_STATUS_4G)

        data_85b = get_duration(data_84b, data_83b, Constants.PROVISION_STATUS_5G)

        time_5g_kpi_list = [data_77a, data_77b, data_78a, data_78b, data_79a,
                            data_79b, data_81a, data_81b, data_83a, data_83b, data_84a, data_84b, data_85a, data_85b]

        for kpi in range(len(time_5g_kpi_list)):
            if isinstance(time_5g_kpi_list[kpi], str):
                time_5g_kpi_list[kpi] = time_5g_kpi_list[kpi].split(",")

        data_77a, data_77b, data_78a, data_78b, data_79a,data_79b,data_81a, data_81b,\
            data_83a, data_83b, data_84a, data_84b, data_85a, data_85b = time_5g_kpi_list

        return {'kpi_77a':data_77a, 'kpi_77b':data_77b, 'kpi_78a': data_78a,'kpi_78b': data_78b,
                'kpi_79a': data_79a, 'kpi_79b': data_79b, 'kpi_81a':data_81a, 'kpi_81b':data_81b,
                'kpi_83a':data_83a,'kpi_83b': data_83b,'kpi_84a': data_84a,'kpi_84b': data_84b,
                'kpi_85a': data_85a,'kpi_85b': data_85b}

    except Exception as exp:
        raise Exception("Exception while calculating the KPIS based on log file {}".format(exp))

def get_duration(kpi_from_subtract, kpi_to_subtract, kpi_def):
    """
    Method to subtract the KPIs and provide the duration between two times
    :param kpi_from_subtract: KPI value from subtract
    :param kpi_to_subtract: KPI value to subtract
    :param kpi_def: KPI definition
    :return: returns the duration between KPISs
    """
    if (kpi_from_subtract and kpi_to_subtract) and (kpi_from_subtract >= kpi_to_subtract):
        kpi_result = str(datetime.strptime(kpi_from_subtract, "%Y-%m-%d %H:%M:%S") -
                         datetime.strptime(kpi_to_subtract, "%Y-%m-%d %H:%M:%S"))
        print("kpi85 check:",kpi_result)
    else:
        kpi_result = ''

    return kpi_result

def update_json_file_anr_datetime(anr_module_name, module_instance_id, data):
    try:
        if not os.path.exists(Constants.JSON_FILE_PATH):
            mapping_data = populate_mapping_file_data(anr_module_name, module_instance_id, data)
            write_to_json_file(Constants.JSON_FILE_PATH, mapping_data)
            os.chmod(Constants.JSON_FILE_PATH, 0o775)

        else:
            mapping_data = read_json_file(Constants.JSON_FILE_PATH)
            #print("success module names:",mapping_data[anr_module_name])
            if mapping_data and anr_module_name not in mapping_data.keys():
                mapping_data.update(
                    populate_mapping_file_data(anr_module_name, module_instance_id, data))

            elif mapping_data and anr_module_name in mapping_data.keys():
                if module_instance_id in mapping_data[anr_module_name].keys():
                    pass

                else:
                    mapping_data[anr_module_name].update({module_instance_id:data})

            elif not mapping_data:
                mapping_data = populate_mapping_file_data(anr_module_name, module_instance_id, data)
            write_to_json_file(Constants.JSON_FILE_PATH, mapping_data)

    except Exception as exp:
        msg = "Exception while appending the Content to  file "
        raise exp

def write_to_json_file(json_file, modified_file_dict):
    try:
        with open(json_file, "w") as write_file_obj:
            json.dump(modified_file_dict, write_file_obj, indent=2)
    except Exception as exp:
        raise Exception("Exception while Writing to the file ".format(exp))

def read_json_file(json_file):
    try:
        with open(json_file, "r") as read_file_obj:
            json_file_dict = json.loads(read_file_obj.read())
    except Exception as exp:
        raise Exception("Exception while Reading the file ".format(exp))
    return json_file_dict

def populate_mapping_file_data(anr_module_name, module_instance_id, data):
    pass

if __name__ == '__main__':
    try:
        module_manager = ModuleManager()
        modules = module_manager.get_all_running_module_instances()
        print("modules:",modules)
        # Extract only the values
        keys_to_filter = ['ANR_2G', 'ANR_3G', 'ANR_4G_IRAT', 'ANR_Blacklisting_and_Cleanup_LTE', 'ANR_5G']
        module_instance_names = [key for module_key in keys_to_filter if module_key in modules
                                 for key, value in modules[module_key].items() if value in ('idle','active')]
        #module_instance_names = ['ANR_2G_abinesh_20250111_104711_584']--->it is dynamic ANR_3G,ANR_5G etc may also come
        kpi_2g3g4g = ['ANR_2G', 'ANR_3G', 'ANR_4G_IRAT', 'ANR_Blacklisting_and_Cleanup_LTE']
        kpi_5g = ['ANR_5G']
        for module_instance_id in module_instance_names:
            anr_module_name, user_name = return_params(module_instance_id)
            report_path = os.path.join(Constants.OUTPUT_DIR, user_name, anr_module_name, module_instance_id)
            config_data = get_config_json(Constants.CONFIG_PATH)
            # from config_data you will get contents of ini file
            file_directory = config_data.get(Constants.REMOTE_VM_DETAILS).get(Constants.REMOTE_FILE_DIR)

            server_details = [config_data.get(Constants.REMOTE_VM_DETAILS).get(Constants.IP),
                              config_data.get(Constants.REMOTE_VM_DETAILS).get(Constants.USER),
                              config_data.get(Constants.REMOTE_VM_DETAILS).get(Constants.PASSWORD)]
            sftp_controller_obj = SFTPHandler(config_data)
            log_filenames = sftp_controller_obj.transfer_file_to_server(
                file_directory, Constants.TARGET_DIR_PATH, module_instance_id, server_details)
            #you will get log file names from the server
            log_file_data = read_log_return_dataframe(log_filenames)
            data_df = generate_data_with_values(log_file_data, config_data)
            anr_report_names = get_file_names(report_path, "*.xlsx")
            iteration = 0
            module_type = ""
            if anr_report_names:
                if anr_report_names[0].lower().__contains__('blocklisting') or anr_report_names[0].lower().__contains__(
                        'lte_anr_blacklisting'):
                    module_type = "Blacklisting"
                else:
                    module_type = "Cleanup"

            if anr_module_name in kpi_2g3g4g:
                for anr_report_name in anr_report_names:
                    iteration = iteration + 1
                    time_kpi = get_status_time_related_2g3g4g_kpi(config_data ,data_df, iteration,module_type)
                    for key, values in time_kpi.items():
                        pass

            elif anr_module_name in kpi_5g:
                for anr_report_name in anr_report_names:
                    iteration = iteration + 1
                    time_5g_kpi = get_status_time_related_5g_kpi(config_data, data_df, iteration)
                    for key, values in time_5g_kpi.items():
                        pass
            update_json_file_anr_datetime(anr_module_name,module_instance_id,data)

    except Exception as exp:
        raise Exception("Script execution failed - {}".format(exp))

