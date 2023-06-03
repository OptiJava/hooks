import pytest as pytest

from hooks import utils


def test_type_list_detect():
    input_list = [1, 2, 3]
    assert utils.is_list_var(input_list) is True
    
    input_str_list = '[1, 2, 3]'
    assert utils.is_list_var(input_str_list) is True
    
    input_str_list_invalid = '["a]'
    assert utils.is_list_var(input_str_list_invalid) is False
    
    input_dict = {"key": "value"}
    assert utils.is_list_var(input_dict) is False
    
    input_str_dict = '{"key": "value"}'
    assert utils.is_list_var(input_str_dict) is False
    
    input_str_dict_invalid = '{"a}'
    assert utils.is_list_var(input_str_dict_invalid) is False
    
    input_int = 1
    assert utils.is_list_var(input_int) is False
    
    input_bool = True
    assert utils.is_list_var(input_bool) is False


def test_type_dict_detect():
    input_list = [1, 2, 3]
    assert utils.is_dict_var(input_list) is False
    
    input_str_list = '[1, 2, 3]'
    assert utils.is_dict_var(input_str_list) is False
    
    input_str_list_invalid = '["a]'
    assert utils.is_dict_var(input_str_list_invalid) is False
    
    input_dict = {"key": "value"}
    assert utils.is_dict_var(input_dict) is True
    
    input_str_dict = '{"key": "value"}'
    assert utils.is_dict_var(input_str_dict) is True
    
    input_str_dict_invalid = '{"a}'
    assert utils.is_dict_var(input_str_dict_invalid) is False
    
    input_int = 1
    assert utils.is_dict_var(input_int) is False
    
    input_bool = True
    assert utils.is_dict_var(input_bool) is False


def test_type_int_detect():
    input_list = [1, 2, 3]
    assert utils.is_int_var(input_list) is False
    
    input_str_list = '[1, 2, 3]'
    assert utils.is_dict_var(input_str_list) is False
    
    input_str_list_invalid = '["a]'
    assert utils.is_int_var(input_str_list_invalid) is False
    
    input_dict = {"key": "value"}
    assert utils.is_int_var(input_dict) is False
    
    input_str_dict = '{"key": "value"}'
    assert utils.is_int_var(input_str_dict) is False
    
    input_str_dict_invalid = '{"a}'
    assert utils.is_int_var(input_str_dict_invalid) is False
    
    input_int = 1
    assert utils.is_int_var(input_int) is True
    
    input_str_int = '1'
    assert utils.is_int_var(input_str_int) is True
    
    input_bool = True
    assert utils.is_int_var(input_bool) is False


def test_is_windows():
    print('操作系统是否为Windows：' + str(utils.is_windows()))


if __name__ == "__main__":
    pytest.main()
