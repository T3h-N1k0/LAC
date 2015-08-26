# coding: utf-8

# Décode fuckin' unicode
class PythonLDAPDecoder:

    """This class can be used to recursively decode
   bytes returned by Python-LDAP, using an encoding
   given in the constructor or as class attribute.

   """
    encoding = 'utf-8'

    def __init__(self, encoding=None):

        if encoding is not None:

            self.encoding = encoding
        elif self.encoding is None:

            raise Exception(
                "No encoding given to {}".format(
                   self.__class__.__name__
                                )
                        )

    def decode(self, data):

        return bytes.decode(data, encoding=self.encoding)

    def decode_dict(self, dct):

        return {
                        self.decode(key):
            map(self.decode, values)
            for key, values in dct.items()
        }

    def decode_dict_list(self, lst):

        return [
            (self.decode(key), self.decode_dict(values))
            for key, values in lst
                ]

    def __call__(self, data):

        return self.decode_dict_list(data)
