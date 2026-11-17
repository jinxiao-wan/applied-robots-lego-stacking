import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, SetParameters


def get_robot_description(node):
    service_name = "/robot_state_publisher/get_parameters"
    param_name = "robot_description"

    try:
        client = node.create_client(GetParameters, service_name, callback_group=ReentrantCallbackGroup())
        if not client.wait_for_service(timeout_sec=2):
            raise TimeoutError(f"Service '{service_name}' is not available.")

        req = GetParameters.Request(names=[param_name])
        future = client.call_async(req)
        rclpy.spin_until_future_complete(node, future)
        res : GetParameters.Response = future.result()

    except Exception as ex:
        raise RuntimeError(f"Unable to query '{service_name}': {type(ex).__name__}: {ex}") from ex

    finally:
        node.destroy_client(client)

    try:
        if len(res.values) != 1:
            raise RuntimeError(f"No value found for {param_name}")
        value = res.values[0]
        valid = value.type == ParameterType.PARAMETER_STRING and bool(value.string_value)
    except Exception:
        valid = False
    if not valid:
        raise RuntimeError(f"Parameter /robot_state_publisher/robot_description is not set.")

    robot_description = value.string_value
    return robot_description

def set_robot_description(node, param_value : str):
    service_name = "/move_group/set_parameters"
    param_name = "robot_description"

    try:
        client = node.create_client(SetParameters, service_name, callback_group=ReentrantCallbackGroup())
        if not client.wait_for_service(timeout_sec=2):
            raise TimeoutError(f"Service '{service_name}' is not available.")

        req = SetParameters.Request(parameters=[
            Parameter(
                name=param_name, 
                value=ParameterValue(
                    type=ParameterType.PARAMETER_STRING,
                    string_value=param_value
                )
            )
        ])
        future = client.call_async(req)
        rclpy.spin_until_future_complete(node, future)
        res : SetParameters.Response = future.result()

    except Exception as ex:
        raise RuntimeError(f"Unable to query '{service_name}': {type(ex).__name__}: {ex}") from ex

    finally:
        node.destroy_client(client)

    if len(res.results) != 1:
        raise RuntimeError(f"No value set for {param_name}")
    value = res.results[0]
    valid = bool(value.successful)
    if not valid:
        raise RuntimeError(f"Parameter /move_group/robot_description is not set. Reason: {value.reason}")
    
    return True

def prepare_pymoveit2():

    rclpy.init()
    node = rclpy.create_node("prepare_pymoveit2")

    robot_description = get_robot_description(node)
    set_robot_description(node, robot_description)
    print("Done setting /move_group/robot_description")

    node.destroy_node()

