import datetime
import platform
import psutil
import os

# These message may be used in other database backend

def get_base_env():
    result = {
        'maxBsonObjectSize': 16777216,
        'maxMessageSizeBytes': 48000000,
        'maxWriteBatchSize': 100000,
        'logicalSessionTimeoutMinutes': 30,
        'minWireVersion': 0,
        'maxWireVersion': 25,
        'localTime': datetime.datetime.now(),
        'readOnly': False,
    }
    return result

def get_host_info():
    result = {
        "system": {
            'currentTime': datetime.datetime.now(),
            'hostname': platform.node(),
            'cpuAddrSize': int(platform.architecture()[0][0:2]),
            'memSizeMB': round(psutil.virtual_memory().total / (1024 ** 2)),
            'memLimitMB': round(psutil.virtual_memory().total / (1024 ** 2)),
            'numCores': psutil.cpu_count(logical=True),
            'numCoresAvailableToProcess': psutil.cpu_count(logical=True),  # 逻辑核心数
            'numPhysicalCores': psutil.cpu_count(logical=False),
            'numCpuSockets': 1,
            'cpuArch': platform.machine(),
            'numaEnabled': False,
            'numNumaNodes': 1
        },
        "os": {
            'type': platform.system(),
            'name': platform.platform(),
            'version': platform.version()
        },
        "extra": {
            # currently can't find method to get these parameters
            'pageSize': 4096,
            'cpuString': 'Intel(R) Core(TM) i9-14900HX'
        }
    }
    return result

def get_build_info():
    result = {
        'version': '8.0.4',
        'gitVersion': 'bc35ab4305d9920d9d0491c1c9ef9b72383d31f9',
        'targetMinOS': 'Windows 7/Windows Server 2008 R2',
        'modules': [],
        'allocator': 'tcmalloc-gperf',
        'javascriptEngine': 'mozjs',
        'sysInfo': 'deprecated',
        'versionArray': [8, 0, 4, 0],  # 8.0.4
        'openssl': {
            'running': 'Windows SChannel'
        },
        'buildEnvironment': {
            'distmod': 'windows',
            'distarch': 'x86_64',
            'cc': 'cl: Microsoft (R) C/C++ Optimizing Compiler Version 19.31.31107 for x64',
            'ccflags': '/nologo /WX /FImongo/platform/basic.h /fp:strict /EHsc /W3 /wd4068 /wd4244 /wd4267 /wd4290 /wd4351 /wd4355 /wd4373 /wd4800 /wd4251 /wd4291 /we4013 /we4099 /we4930 /errorReport:none /MD /O2 /Oy- /bigobj /utf-8 /permissive- /Zc:__cplusplus /Zc:sizedDealloc /volatile:iso /diagnostics:caret /std:c++20 /Gw /Gy /Zc:inline',
            'cxx': 'cl: Microsoft (R) C/C++ Optimizing Compiler Version 19.31.31107 for x64',
            'cxxflags': '/TP',
            'linkflags': '/nologo /DEBUG /INCREMENTAL:NO /LARGEADDRESSAWARE /OPT:REF',
            'target_arch': 'x86_64',
            'target_os': 'windows',
            'cppdefines': 'SAFEINT_USE_INTRINSICS 0 PCRE2_STATIC NDEBUG BOOST_ALL_NO_LIB _UNICODE UNICODE _SILENCE_CXX17_ALLOCATOR_VOID_DEPRECATION_WARNING _SILENCE_CXX17_OLD_ALLOCATOR_MEMBERS_DEPRECATION_WARNING _SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING _SILENCE_ALL_CXX20_DEPRECATION_WARNINGS _CONSOLE _CRT_SECURE_NO_WARNINGS _ENABLE_EXTENDED_ALIGNED_STORAGE _SCL_SECURE_NO_WARNINGS _WIN32_WINNT 0x0A00 BOOST_USE_WINAPI_VERSION 0x0A00 NTDDI_VERSION 0x0A000000 ABSL_FORCE_ALIGNED_ACCESS BOOST_ENABLE_ASSERT_DEBUG_HANDLER BOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF BOOST_LOG_NO_SHORTHAND_NAMES BOOST_LOG_USE_NATIVE_SYSLOG BOOST_LOG_WITHOUT_THREAD_ATTR BOOST_MATH_NO_LONG_DOUBLE_MATH_FUNCTIONS BOOST_SYSTEM_NO_DEPRECATED BOOST_THREAD_USES_DATETIME BOOST_THREAD_VERSION 5'
        },
        'bits': 64,
        'debug': False,
        'maxBsonObjectSize': 16777216,
        'storageEngines': ['devnull', 'wiredTiger'],
    }
    return result

if __name__ == '__main__':
    print(get_host_info())