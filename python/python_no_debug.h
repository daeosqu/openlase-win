// pythonh_release.h
#pragma once
#ifdef _DEBUG
  #pragma push_macro("_DEBUG")
  #undef _DEBUG
  #include <Python.h>
  #pragma pop_macro("_DEBUG")
#else
  #include <Python.h>
#endif
