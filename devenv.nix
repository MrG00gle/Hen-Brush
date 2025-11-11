{
  pkgs,
  lib,
  config,
  ...
}:
{

  cachix.enable = true;
  

  packages = [
    pkgs.socat
    pkgs.python312Packages.pygobject3
    pkgs.gobject-introspection
    pkgs.gtk4
    pkgs.libadwaita
    pkgs.gst_all_1.gst-plugins-base
  ];


  languages.python = {
    enable = true;
    version = "3.12";
    venv = {
        enable = true;
        requirements = ''
        pip
        colorama
        pytest
        numpy
        pyserial
        pycairo
        PyGObject
        textual
        '';
    };
  };

  # Set up GIO_EXTRA_MODULES for Gtk4 to correctly load extensions
  # e.g. for gsettings schemas
  #env.GIO_EXTRA_MODULES.value = "\${config.languages.python.venv.path}/${config.languages.python.package.pythonDir}/girepository-1.0";

  # Export required GSETTINGS schemes (needed for libadwaita etc.)
  #enterShell = ''
   # export XDG_DATA_DIRS="$XDG_DATA_DIRS:$PYTHON_VENV_PATH/${config.languages.python.package.pythonDir}/share/glib-2.0/schemas"
  #'';
  
#    scripts.create-venv.exec = ''
#    if [ ! -d "$DEVENV_ROOT/venv" ]; then
#        sudo rm -r $DEVENV_ROOT/venv
#        python -m venv venv
#        source $DEVENV_ROOT/venv/bin/activate
#        pip install --upgrade pip
#    fi
#
#  '';

#    enterShell = ''
#    # Create a Python virtual environment for IDE compatibility
#    if [ ! -L "$DEVENV_ROOT/venv" ]; then
#        ln -s "$DEVENV_STATE/venv/" "$DEVENV_ROOT/venv"
#    fi
#  '';

}

