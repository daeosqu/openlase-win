ifeq ($(wildcard $(addsuffix /rm,$(subst :, ,$(PATH)))),)
	MSVC:=1
	RM=del /S
	RM_R=rmdir /S /Q
else
	MSVC:=
	RM_R=$(RM) -r
endif

CMAKE_BUILD_OPTS := -G "Ninja"
BUILD_TYPE := Release
BUILD_DIR := build-$(BUILD_TYPE)

all: ctest

$(BUILD_DIR):
	mkdir $@

clean:
	$(RM_R) $(BUILD_DIR)

$(BUILD_DIR)/ALL_BUILD.vcxproj: ./Makefile ./CMakeLists.txt | $(BUILD_DIR)
	cmake -S . -B $(BUILD_DIR) $(CMAKE_BUILD_OPTS) -DCMAKE_BUILD_TYPE=$(BUILD_TYPE)

ctest: $(BUILD_DIR)/ALL_BUILD.vcxproj
	cd $(BUILD_DIR) && ctest -C ${BUILD_TYPE}

ctest-devel: $(BUILD_DIR)/ALL_BUILD.vcxproj
	cd $(BUILD_DIR) && ctest -C $(BUILD_TYPE) --output-on-failure --stop-on-failure -VV
