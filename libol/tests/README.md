# tests

## Unix

```
cd tests
cmake -S . -B build
cd build && ctest --output-on-failure --stop-on-failure
```

## Windows (MSVC)

Run in Developer PowerShell for VS 2022.

```
cd tests
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release
cd build && ctest --output-on-failure --stop-on-failure -C Release
```
