## FreeCAD Curves and Surfaces WorkBench 简单汉化，比较菜不同步上游更新，可能还有汉化引起的bug
![Curves Workbench](https://github.com/q921057310-byte/CurvesWB-cn/blob/main/docs/pics/d5a16e90-09a2-4dcb-8d2c-e0972a98fb8b.png)


FreeCAD 曲线和曲面工作台（简易汉化版）
水平有限，未同步上游更新，可能存在汉化引发的 bug


这主要用于 NURBS 曲线与曲面操作。本工作台基于 FreeCAD 主开发分支开发。

重要说明

本工作台为实验性工具，不可用于正式生产工作。

不适合初学者使用，需要具备一定 FreeCAD 基础。

本项目本质为个人几何算法实验项目。

安装方法，汉化版不支持插件管理器安装。

进入个人 FreeCAD 目录：

Linux：/home/用户名/.local/share/FreeCAD/

Windows：%APPDATA%\FreeCAD\Mod\

macOS：/Users/用户名/Library/Preferences/FreeCAD/

进入 Mod 文件夹，不存在则新建



</details>
This is a python workbench for [FreeCAD](https://www.freecad.org), with a collection of tools, mainly for NURBS curves and surfaces.  
This workbench is developed for FreeCAD main develoment branch.

## Important Notes  
* This workbench is EXPERIMENTAL and should NOT be used for any serious work.
* This workbench is not suitable for beginners. A good knowledge of FreeCAD is needed.
* This workbench is essentially my personal playground for experimenting with geometric algorithms.

## Installation 
There are 2 methods to install Curves WB:

#### Automatic (recommended)
For FreeCAD version 0.17 or higher it's preferred to install this workbench with the [FreeCAD's addon manager](https://wiki.freecad.org/Std_AddonMgr) under the label **Curves**.

#### Manual
<details>
<summary>Expand this section for instructions on Manual install</summary>

- Move to the location of your personal FreeCAD folder 
    - On Linux it is usually `/home/username/.local/share/FreeCAD/`
    - On Windows it is `%APPDATA%\FreeCAD\Mod\` which is usually `C:\Users\username\Appdata\Roaming\FreeCAD\`
    - On macOS it is usually `/Users/username/Library/Preferences/FreeCAD/`
- Move to the Mod folder : `cd ./Mod` (create the `Mod/` folder beforehand if it doesn't exist)
- `git clone https://github.com/tomate44/CurvesWB`
- Start FreeCAD

</details><br/>

## Documentation
The Curves workbench documentation can be found on the [FreeCAD wiki](https://wiki.freecad.org/Curves_Workbench).

## Feedback  
The main and recommended channel for discussion, feedback, suggestions, and patches is the following discussion of FreeCAD's forum : [Curves workbench](https://forum.freecad.org/viewtopic.php?f=8&t=22675)

## Contributing
#### Reporting issues
Issues should first be reported in the [FreeCAD forum discussion](https://forum.freecad.org/viewtopic.php?f=8&t=22675). A minimal FreeCAD file demonstrating the bug should be attached.  
Issues reported in Github may be unnoticed. A minimal FreeCAD file demonstrating the bug should be attached to the issue report, with *.FCStd extension renamed to *.zip

#### Contributing code
Code contribution is NOT encouraged and should first be discussed in [FreeCAD forum discussion](https://forum.freecad.org/viewtopic.php?f=8&t=22675).

#### Contributing documentation
The workbench documention is not extensive.  
Contributing documentation on [FreeCAD wiki](https://wiki.freecad.org/Curves_Workbench) is welcome.

## License  
CurvesWB is released under the LGPL2.1+ license. See [LICENSE](https://github.com/tomate44/CurvesWB/blob/main/LICENSES/LGPL-2.1.txt).
