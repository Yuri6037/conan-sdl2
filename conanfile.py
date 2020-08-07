from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os


class SDL2Conan(ConanFile):
    name = "sdl2"
    description = "Access to audio, keyboard, mouse, joystick, and graphics hardware via OpenGL, Direct3D and Vulkan"
    topics = ("conan", "sdl2", "audio", "keyboard", "graphics", "opengl")
    url = "https://github.com/Yuri6037/conan-sdl2"
    homepage = "https://www.libsdl.org"
    license = "Zlib"
    exports_sources = ["CMakeLists.txt", "patches/*"]
    generators = ["cmake", "pkg_config"]
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "directx": [True, False],
        "alsa": [True, False],
        "jack": [True, False],
        "pulse": [True, False],
        "sndio": [True, False],
        "nas": [True, False],
        "x11": [True, False],
        "xcursor": [True, False],
        "xinerama": [True, False],
        "xinput": [True, False],
        "xrandr": [True, False],
        "xscrnsaver": [True, False],
        "xshape": [True, False],
        "xvm": [True, False],
        "wayland": [True, False],
        "directfb": [True, False],
        "iconv": [True, False],
        "video_rpi": [True, False],
        "sdl2main": [True, False]
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "directx": False,
        "alsa": False,
        "jack": False,
        "pulse": False,
        "sndio": False,
        "nas": False,
        "x11": True,
        "xcursor": True,
        "xinerama": True,
        "xinput": True,
        "xrandr": True,
        "xscrnsaver": True,
        "xshape": False,
        "xvm": False,
        "wayland": True,
        "directfb": False,
        "iconv": False,
        "video_rpi": False,
        "sdl2main": False
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"
    _cmake = None

    def build_requirements(self):
        self.build_requires("sdl2-sys-require/1.0@bp3d/stable")
        if self.options.iconv:
            self.build_requires("libiconv/1.16")

        if self.settings.os == "Linux" and tools.os_info.is_linux:
            self.build_requires("xorg/system")
            if not tools.which("pkg-config"):
                self.build_requires("pkg-config_installer/0.29.2@bincrafters/stable")
            if self.options.alsa:
                self.build_requires("libalsa/1.1.9")
            if self.options.pulse:
                self.build_requires("pulseaudio/13.0@bincrafters/stable")
            self.build_requires("opengl/system")

    def config_options(self):
        if self.settings.os != "Linux":
            self.options.remove("alsa")
            self.options.remove("jack")
            self.options.remove("pulse")
            self.options.remove("sndio")
            self.options.remove("nas")
            self.options.remove("x11")
            self.options.remove("xcursor")
            self.options.remove("xinerama")
            self.options.remove("xinput")
            self.options.remove("xrandr")
            self.options.remove("xscrnsaver")
            self.options.remove("xshape")
            self.options.remove("xvm")
            self.options.remove("wayland")
            self.options.remove("directfb")
            self.options.remove("video_rpi")
        if self.settings.os != "Windows":
            self.options.remove("directx")

    def configure(self):
        lst = ["jack", "sndio", "nas", "esd", "arts", "wayland", "directfb"]
        for v in lst: #Attempt at passing options
            self.options["sdl2-sys-require"][v] = self.options[v]
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        if self.settings.compiler == "Visual Studio":
            del self.options.fPIC
        if (self.settings.os == "Macos" and not self.options.shared):
            self.options.shared = True #For some reasons SDL2 refuses to statically link any application under MacOS Catalina 10.15, so just force it as shared
        if self.settings.os == "Macos" and not self.options.iconv:
            self.options.iconv = True
            #raise ConanInvalidConfiguration("On macOS iconv can't be disabled") Fucking Idiot ! YOU DO NOT RAISE INSTEAD YOU SET THE OPTION OH MY GOD FUCKER

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = "SDL2-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

        if "patches" in self.conan_data and self.version in self.conan_data["patches"]:
            for patch in self.conan_data["patches"][self.version]:
                tools.patch(**patch)

    def build(self):
        # ensure sdl2-config is created for MinGW
        tools.replace_in_file(os.path.join(self._source_subfolder, "CMakeLists.txt"),
                              "if(NOT WINDOWS OR CYGWIN)",
                              "if(NOT WINDOWS OR CYGWIN OR MINGW)")
        tools.replace_in_file(os.path.join(self._source_subfolder, "CMakeLists.txt"),
                              "if(NOT (WINDOWS OR CYGWIN))",
                              "if(NOT (WINDOWS OR CYGWIN OR MINGW))")
        self._build_cmake()

    def _check_pkg_config(self, option, package_name):
        if option:
            pkg_config = tools.PkgConfig(package_name)
            if not pkg_config.provides:
                raise ConanInvalidConfiguration("package %s is not available" % package_name)

    def _check_dependencies(self):
        if self.settings.os == "Linux":
            self._check_pkg_config(self.options.jack, "jack")
            self._check_pkg_config(self.options.wayland, "wayland-client")
            self._check_pkg_config(self.options.wayland, "wayland-protocols")
            self._check_pkg_config(self.options.directfb, "directfb")

    def _configure_cmake(self):
        if not self._cmake:
            self._check_dependencies()

            self._cmake = CMake(self)
            # FIXME: self.install_folder not defined? Neccessary?
            self._cmake.definitions["CONAN_INSTALL_FOLDER"] = self.install_folder
            if self.settings.os != "Windows":
                if not self.options.shared:
                    self._cmake.definitions["SDL_STATIC_PIC"] = self.options.fPIC
            if self.settings.compiler == "Visual Studio" and not self.options.shared:
                self._cmake.definitions["HAVE_LIBC"] = True
            self._cmake.definitions["SDL_SHARED"] = self.options.shared
            self._cmake.definitions["SDL_STATIC"] = not self.options.shared
            if self.settings.os == "Linux":
                # See https://github.com/bincrafters/community/issues/696
                self._cmake.definitions["SDL_VIDEO_DRIVER_X11_SUPPORTS_GENERIC_EVENTS"] = 1

                self._cmake.definitions["ALSA"] = self.options.alsa
                if self.options.alsa:
                    self._cmake.definitions["HAVE_ASOUNDLIB_H"] = True
                    self._cmake.definitions["HAVE_LIBASOUND"] = True
                self._cmake.definitions["JACK"] = self.options.jack
                self._cmake.definitions["PULSEAUDIO"] = self.options.pulse
                self._cmake.definitions["SNDIO"] = self.options.sndio
                self._cmake.definitions["NAS"] = self.options.nas
                self._cmake.definitions["VIDEO_X11"] = self.options.x11
                if self.options.x11:
                    self._cmake.definitions["HAVE_XEXT_H"] = True
                self._cmake.definitions["VIDEO_X11_XCURSOR"] = self.options.xcursor
                if self.options.xcursor:
                    self._cmake.definitions["HAVE_XCURSOR_H"] = True
                self._cmake.definitions["VIDEO_X11_XINERAMA"] = self.options.xinerama
                if self.options.xinerama:
                    self._cmake.definitions["HAVE_XINERAMA_H"] = True
                self._cmake.definitions["VIDEO_X11_XINPUT"] = self.options.xinput
                if self.options.xinput:
                    self._cmake.definitions["HAVE_XINPUT_H"] = True
                self._cmake.definitions["VIDEO_X11_XRANDR"] = self.options.xrandr
                if self.options.xrandr:
                    self._cmake.definitions["HAVE_XRANDR_H"] = True
                self._cmake.definitions["VIDEO_X11_XSCRNSAVER"] = self.options.xscrnsaver
                if self.options.xscrnsaver:
                    self._cmake.definitions["HAVE_XSS_H"] = True
                self._cmake.definitions["VIDEO_X11_XSHAPE"] = self.options.xshape
                if self.options.xshape:
                    self._cmake.definitions["HAVE_XSHAPE_H"] = True
                self._cmake.definitions["VIDEO_X11_XVM"] = self.options.xvm
                if self.options.xvm:
                    self._cmake.definitions["HAVE_XF86VM_H"] = True
                self._cmake.definitions["VIDEO_WAYLAND"] = self.options.wayland
                self._cmake.definitions["VIDEO_DIRECTFB"] = self.options.directfb
                self._cmake.definitions["VIDEO_RPI"] = self.options.video_rpi
                self._cmake.definitions["HAVE_VIDEO_OPENGL"] = True
                self._cmake.definitions["HAVE_VIDEO_OPENGL_EGL"] = True
            elif self.settings.os == "Windows":
                self._cmake.definitions["DIRECTX"] = self.options.directx

            self._cmake.configure(build_dir=self._build_subfolder)
        return self._cmake

    def _build_cmake(self):
        if self.settings.os == "Linux":
            if self.options.pulse:
                os.rename("libpulse.pc", "libpulse-simple.pc")
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy(pattern="COPYING.txt", dst="license", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install(build_dir=self._build_subfolder)
        tools.rmdir(os.path.join(self.package_folder, "cmake"))

    def _add_libraries_from_pc(self, library, static=None):
        if static is None:
            static = not self.options.shared
        pkg_config = tools.PkgConfig(library, static=static)
        libs = [lib[2:] for lib in pkg_config.libs_only_l]  # cut -l prefix
        lib_paths = [lib[2:] for lib in pkg_config.libs_only_L]  # cut -L prefix
        self.cpp_info.libs.extend(libs)
        self.cpp_info.libdirs.extend(lib_paths)
        self.cpp_info.sharedlinkflags.extend(pkg_config.libs_only_other)
        self.cpp_info.exelinkflags.extend(pkg_config.libs_only_other)

    def package_id(self):
        del self.info.options.sdl2main

    @staticmethod
    def _chmod_plus_x(filename):
        if os.name == "posix":
            os.chmod(filename, os.stat(filename).st_mode | 0o111)

    def package_info(self):
        sdl2_config = os.path.join(self.package_folder, "bin", "sdl2-config")
        self._chmod_plus_x(sdl2_config)
        self.output.info("Creating SDL2_CONFIG environment variable: %s" % sdl2_config)
        self.env_info.SDL2_CONFIG = sdl2_config
        self.output.info("Creating SDL_CONFIG environment variable: %s" % sdl2_config)
        self.env_info.SDL_CONFIG = sdl2_config
        self.cpp_info.libs = [lib for lib in tools.collect_libs(self) if "2.0" not in lib]
        if not self.options.sdl2main:
            self.cpp_info.libs = [lib for lib in self.cpp_info.libs]
        else:
            # ensure that SDL2main is linked first
            sdl2mainlib = "SDL2main"
            if self.settings.build_type == "Debug":
                sdl2mainlib = "SDL2maind"
            self.cpp_info.libs.insert(0, self.cpp_info.libs.pop(self.cpp_info.libs.index(sdl2mainlib)))
        self.cpp_info.includedirs.append(os.path.join("include", "SDL2"))
        if self.settings.os == "Linux":
            self.cpp_info.system_libs.extend(["dl", "rt", "pthread"])
            if self.options.jack:
                self._add_libraries_from_pc("jack")
            if self.options.sndio:
                self._add_libraries_from_pc("sndio")
            if self.options.nas:
                self.cpp_info.libs.append("audio")
            if self.options.directfb:
                self._add_libraries_from_pc("directfb")
            if self.options.video_rpi:
                self.cpp_info.libs.append("bcm_host")
                self.cpp_info.includedirs.extend(["/opt/vc/include",
                                                  "/opt/vc/include/interface/vcos/pthreads",
                                                  "/opt/vc/include/interface/vmcs_host/linux"])
                self.cpp_info.libdirs.append("/opt/vc/lib")
                self.cpp_info.sharedlinkflags.append("-Wl,-rpath,/opt/vc/lib")
                self.cpp_info.exelinkflags.append("-Wl,-rpath,/opt/vc/lib")
        elif self.settings.os == "Macos":
            self.cpp_info.frameworks.extend(["Cocoa", "Carbon", "IOKit", "CoreVideo", "CoreAudio", "AudioToolbox", "ForceFeedback"])
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs.extend(["user32", "gdi32", "winmm", "imm32", "ole32", "oleaut32", "version", "uuid", "advapi32", "setupapi", "shell32"])
        self.cpp_info.names["cmake_find_package"] = "SDL2"
        self.cpp_info.names["cmake_find_package_multi"] = "SDL2"
