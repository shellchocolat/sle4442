import sys
from smartcard.scard import * # pip3 install pyscard
import smartcard.util

# https://www.hidglobal.com/sites/default/files/resource_files/plt-03099_a.3_-_omnikey_sw_dev_guide.pdf


class Sle4442():
    def __init__(self):

        self.SELECT = [0xff, 0xa4, 0x00, 0x00, 0x01, 0x06]
        self.READ = [0xff, 0xb0, 0x00]
        self.READ_PROT = [0xff, 0x3a, 0x00]
        self.VERIFY_PIN = [0xff, 0x20, 0x00, 0x00]
        self.MODIFY_PIN = [0xff, 0x21, 0x00, 0x00]
        self.WRITE = [0xff, 0xd6,0x00]

        hresult, self.hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
        if hresult != SCARD_S_SUCCESS:
            print('Failed to establish context: ' + SCardGetErrorMessage(hresult))
        print('Context established!')

        hresult, readers = SCardListReaders(self.hcontext, [])
        if hresult != SCARD_S_SUCCESS:
            print('Failed to list readers: '+ SCardGetErrorMessage(hresult))
        print('PCSC Readers: ', readers)

        if len(readers) < 1:
            print('No smart card readers')
        reader = readers[0]
        print("Using reader: ", reader)

        hresult, self.hcard, self.dwActiveProtocol = SCardConnect(self.hcontext, reader, SCARD_SHARE_SHARED, SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1)
        if hresult != SCARD_S_SUCCESS:
            print('Unable to connect: ' + SCardGetErrorMessage(hresult))
        print('Connected with active protocol: ', self.dwActiveProtocol)

        hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, self.SELECT)
        if hresult != SCARD_S_SUCCESS:
            print('Failed to transmit: ' + SCardGetErrorMessage(hresult))

        
    def convert_sw_hex(self, sw):
        return hex(sw[0]), hex(sw[1])

    def modify_pin(self, old_pin, new_pin):
        """
        not tested
        """

        len_new_pin = len(new_pin)
        len_old_pin = len(old_pin)
        len_tot= [len_old_pin + len_new_pin]
        hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, self.MODIFY_PIN + len_tot + old_pin + new_pin)
        if hresult != SCARD_S_SUCCESS:
            print('Failed to transmit: ' + SCardGetErrorMessage(hresult))
        return True

    def verify_pin(self, pin):
        """
            verify the pin. The pin is 3 bytes long

            pin is a list -> pin = [0xFF, 0xFF, 0xFF]

            Be carefull, only 3 attempts. More attempt and you couldn't lock your card, and not be 
            able to write anymore.
        """
        try:
            hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, self.VERIFY_PIN + [0x03] + pin)
            if hresult != SCARD_S_SUCCESS:
                print('Failed to transmit: ' + SCardGetErrorMessage(hresult))
        except Exception as e:
            print(str(e))
            return "?", "?"

        return self.convert_sw_hex(response[-2:]), response[0:-2]

    def get_number_left_try(self, error):
        """
          return the number of left try

        error -> the sw from verify_pin()

        sw = (0x63, 0xCx)  -> x number of try left
        """
        left_try = 3
        if error[1][3] == '0':
            left_try =  3
        elif error[1][3] == '2':
            left_try =  2
        elif error[1][3] == '1':
            left_try =  1
        else:
            left_try =  0

        return left_try



    def read(self, address_start=0, address_end=255):
        """
            read the total or partial memory card
        """
        try:
            range_address = [address_start, address_end]
            hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, self.READ + range_address)
            if hresult != SCARD_S_SUCCESS:
                print('Failed to transmit: ' + SCardGetErrorMessage(hresult))
        except Exception as e:
            print(str(e))
            return "?", "?"

        return self.convert_sw_hex(response[-2:]), response[0:-2]


    def write(self, address_start, data):
        """
            write data on memory card if pin is correct
            must perform a verify_pin() before

            data is a list -> data = [0x01, 0x02, 0x03, 0x4, ...]
            address_start is a byte -> address_start = 0x50

            Be carefull, don't overwrite the first bytes so to not brick your card
        """
        try:
            r = data
            len_r = [len(r)]
            address = [address_start]
            hresult, response = SCardTransmit(self.hcard, self.dwActiveProtocol, self.WRITE + address + len_r + r)
            if hresult != SCARD_S_SUCCESS:
                print('Failed to transmit: ' + SCardGetErrorMessage(hresult))
        except Exception as e:
            print(str(e))
            return "?", "?"
        
        return self.convert_sw_hex(response[-2:]), response[0:-2]


    def disconnect(self):
        try:
            hresult = SCardDisconnect(self.hcard, SCARD_UNPOWER_CARD)
            if hresult != SCARD_S_SUCCESS:
                print('Failed to disconnect: ' + SCardGetErrorMessage(hresult))
            print('Disconnected')
        except Exception as e:
            print(str(e))
            return False
        return True


    def release_context(self):
        try:
            hresult = SCardReleaseContext(self.hcontext)
            if hresult != SCARD_S_SUCCESS:
                print('Failed to release context: ' + SCardGetErrorMessage(hresult))
            print('Released context.')
        except Exception as e:
            print(str(e))
            return False
        return True

def main():
    sle4442 = Sle4442()
    sw, _ = sle4442.verify_pin(pin=[0xFF, 0xFF, 0xFF])
    if sw == ('0x90', '0x0'): 
        print('[OK] transmit VERIFY_PIN: %s' %format(sw))
    else:
        print('[KO] transmit VERIFY_PIN: %s' %format(sw))
        left_try = sle4442.get_number_left_try(sw)
        print('\t number of left try: %s' %(left_try) )

    sw, data = sle4442.read(address_start=0, address_end=255)
    if sw == ('0x90', '0x0'): 
        print('[OK] transmit READ: %s' %format(sw))
        print(data)

    sw, _ = sle4442.write(address_start=0x50, data=[0x00, 0x00, 0x00, 0x00])
    if sw == ('0x90', '0x0'): 
        print('[OK] transmit WRITE: %s' %format(sw))

    sw, data = sle4442.read(address_start=0, address_end=255)
    if sw == ('0x90', '0x0'): 
        print('[OK] transmit READ: %s' %format(sw))
        print(data)


    sle4442.disconnect()
    sle4442.release_context()

if __name__ == '__main__':
    main()


