# class CachedProperty(object):
#     def __init__(self, prop):
#         self.is_cached = False
#         self.value = None
#         self.caller = property(prop)
#     def __call__(self, fun):
#         return self
#     def reset(self):
#         self.is_cached = False
#     def __get__(self, obj, type=None):
#         if not self.is_cached:
#             self.value = self.caller.fget(obj)
#             self.is_cached = True
#         return self.value
# CachedProperty.dummy = CachedProperty(False)
#
# class CachedCall(object):
#     ''' NEEDS ADDITION OF CHECKING ARGUMENTS AND MAPPING THOSE TO A RETURN VALUE
#     '''
#     def __init__(self, caller):
#         self.is_cached = False
#         self.caller = caller
#         self.cache = {}
#     def __call__(self, *args, **kwargs):
#         hsh = hash(tuple(list(args) + list(kwargs.items())))
#         if hsh not in self.cache:
#             print(self)
#             print(args)
#             print(kwargs)
#             self.cache[hsh] = self.caller(*args, **kwargs)
#         return self.cache[hsh]
#     def reset(self):
#         self.cache = {}
#
# if __name__ == "__main__":
#     class Obj(object):
#         def __init__(self):
#             self.x = 5
#
#         # @CachedProperty
#         # def prop(self):
#         #     return self.x
#
#         @CachedCall
#         def func(self, a=1, b=2, c=3):
#             print(self)
#             print("A = %s, B = %s, C = %s, X = %s" % (str(a), str(b), str(c), str(self.x)))
#             self.x += 1
#
#     o = Obj()
#     # print(o.prop)
#     # o.x = 10
#     # print(o.prop)
#     # o.prop #lolwut?
#     # print(o.prop)
#     print(o.func(1,2,3))
#     print(o.func(1,2))
#     print(o.func(1,2,3))