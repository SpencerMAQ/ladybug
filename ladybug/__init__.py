"""Ladybug library for Grasshopper."""
import sys

# This is a variable to check if the library is a [+] library.
setattr(sys.modules[__name__], 'isplus', True)
# sys.modules simply makes it so that the the ladybug package would have an isplus attribute set to true
# i.e. ladybug.isplus = True
