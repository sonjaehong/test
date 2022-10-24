
import base64
import json
try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO
from pprint import pprint



class VedDecoder():
    
    def ved_to_base64(self, ved:str):
        remove_version = ved[1:]
        b64 = remove_version + '=' * (4 - len(remove_version) % 4)
        b64 = b64.replace('-', '+').replace('_', '/')
        return b64


    def base64_decode(self, b64_string):
        return base64.b64decode(b64_string)
        

    def varints_decode(self, buffer):
        '''
            b'\x96\x01'                   # 1. int를 protobuf로 인코딩한 값을 바이트 단위로
            b'\x96' = 150, b'\x01' = 1    # 2. ord()로 유니코드 정수를 반환 
            10010110 00000001             # 3. 반환된 정수를 이진수로 변환
            0010110  0000001             # 4. msb 제거
            0000001  0010110             # 5. Varint는 최하위 그룹을 먼저 위치시키는 방식을 택한다. (least significant group first). 그러므로  우리가 이해하는 숫자로 인식하기 위해선 7비트 단위 그룹의 위치를 서로 바꾸어 주어야 한다.
                1  0010110             # 6. 의미 없는 비트를 버린 뒤 연결하면 끝

            10010110 > 128 + 16 + 4 + 2 = 150
        '''
        
        results = []
        buffer = BytesIO(buffer)
        while True:
            byte = buffer.read(1)
            if byte == b'':
                break
            int_val = ord(byte)
            binary_val = bin(int_val)[2:].zfill(8)
            remove_msb = binary_val[1:]
            results.append(remove_msb)

        binary_join = ''.join(reversed(results))#.lstrip('0')
        convert_to_int = int(binary_join, 2)
        
        return convert_to_int


    def field_decode(self, buffer):
        '''
            b'\x08'             # example
            b'\x08' = 8         # 1. ord()로 유니코드 정수를 반환
            0000 1000           # 3. 반환된 정수를 이진수로 변환
            000 1000           # 4.msb 제거
                000           # 5 .마지막 3비트는 와이어 유형 (0)
            000 0001           # 5. 오른쪽으로 3만큼 시프트하여 필드 번호(1)를 얻는다 
            
            * feild는 1부터 15까지의 범위값을 갖는 태그는 숫자와 필드 타입을 포함하여 1바이트로 인코딩된다. 16부터 2047까지의 범위값의 태그는 2바이트를 취한다.
        '''
        
        field_type = {
            0: 'VARINT',	    # int32, int64, uint32, uint64, sint32, sint64, bool, enum
            1: 'I64',	        # fixed64, sfixed64, double
            2: 'LEN',	        # string, bytes, embedded messages, packed repeated fields
            3: 'SGROUP',	    # group start (deprecated)
            4: 'EGROUP',	    # group end (deprecated)
            5: 'I32',	        # fixed32, sfixed32, float
        }
        
        int_val = int.from_bytes(buffer, 'little')
        binary_val = bin(int_val)[2:].zfill(8)
        remove_msb = binary_val[1:]
        
        wire_type = remove_msb[-3:]
        wire_type = int(wire_type, 2)
        field_num = int(remove_msb.lstrip('0'), 2) >> 3
        
        return field_num, field_type[wire_type]
        

    def buffer_distributor(self, buffer):
        '''
            1. protocol buffer 를 타입별로 나누어 순서대로 분배한다.
        '''
        bytes = BytesIO(buffer)
        cnt = 0
        field_cnt = 0
        is_field = True
        type_check = None
        is_length_prefix, length_prefix = False, 0
        buffer_dict = []
        while True:
            if is_field:
                if field_cnt < 15:
                    byte = bytes.read(1)
                    cnt += 1
                else:
                    byte = bytes.read(2)
                    cnt += 2
                if byte == b'':
                    break

                field, type = self.field_decode(byte)
                if type in ['VARINT', 'I64', 'LEN', 'SGROUP', 'EGROUP', 'I32']:
                    type_check = type
                else :
                    raise Exception('Unknown type')
                field_cnt = field
                is_field = False
                buffer_dict.append({'field': field, 'type': type,'value': b''})
                
            else:
                byte = bytes.read(1)
                
                if type_check == 'VARINT':
                    int_val = int.from_bytes(byte, 'little')
                    binary_val = bin(int_val)[2:].zfill(8)
                    is_msb = int(binary_val[:1])
                    if is_msb:
                        buffer_dict[-1]['value'] += byte
                    else:
                        buffer_dict[-1]['value'] += byte
                        type_check = None
                        is_field = True
                        
                elif type_check == 'LEN':
                    if not is_length_prefix:
                        length_prefix = self.varints_decode(byte) - 1
                        is_length_prefix = True
                    else:
                        if length_prefix > 0:
                            buffer_dict[-1]['value'] += byte
                            length_prefix -= 1
                        else:
                            buffer_dict[-1]['value'] += byte
                            is_length_prefix = False
                            type_check = None
                            is_field = True
                            field_cnt += 1
                            
                cnt += 1
            
        for b in  buffer_dict:
            if b['type'] == 'VARINT':
                b['value'] = self.varints_decode(b['value'])

        return buffer_dict
        

    def get_json(self, ved_string, result):
        json_data = {}
        # json_data['ved'] = ved_string
        json_data['decode'] = result
        return json_data
        

    def decode(self, ved_string, json=True):
        ved = self.ved_to_base64(ved_string)
        print(ved)
        buffer = self.base64_decode(ved)
        print(buffer)
        result = self.buffer_distributor(buffer)
        print(result)
        if json:
            return self.get_json(ved_string, result)
        else:
            return result




if __name__ == '__main__':
    vd = VedDecoder()
    result = vd.decode('2ahUKEwiewZLqte36AhXMBt4KHRTpDXwQ3IgCKAB6BAhsEAA', json=True)
    pprint(result)
    

   
    '''
    varint는 msb 여부로 길이 판단
    string은 length prefix로 길이 판단 
    
    field 1번 > hveid
    field 2번 > type
    field 5번 > sub_link_position
    '''
    
    # b'j\x15\n\x13\x08\xbb\xa8\xea\xd3\xd8\xd7\xfa\x02\x15a\x98V\x01\x1d\xc1U\x01\xf5\x10\xc8\xda\x01(\x02z\x04\x08\x07\x10\t'
    # print(vd.field_decode(b'\n'))
    # print(vd.field_decode(b'\x13'))
    # print(vd.field_decode(b'\x08'))
    # print(vd.field_decode(b'z'))