# 自动注册机使用指南

## 问题分析

脚本运行测试结果显示：

✅ 临时邮箱网站 `http://mail0.dfyx.xyz/` 可以正常访问
✅ 注册网站 `https://www.daydaymap.com/user/register` 可以正常访问
❌ 缺少ChromeDriver，导致Selenium无法初始化

## ChromeDriver安装步骤

### 1. 检查Chrome浏览器版本

1. 打开Chrome浏览器
2. 在地址栏输入 `chrome://settings/help`
3. 记录Chrome浏览器的版本号（例如：120.0.6099.109）

### 2. 下载匹配的ChromeDriver

1. 访问ChromeDriver下载页面：[https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)
2. 下载与您Chrome浏览器版本完全匹配的ChromeDriver版本
3. 如果找不到完全匹配的版本，可以下载最接近的版本（通常前3位数字匹配即可）

### 3. 安装ChromeDriver

将下载的ZIP文件解压，得到`chromedriver.exe`文件，然后放在以下任一位置：

- **推荐**：直接放在当前目录 `D:\safePro\Register-tools\`
- 或者：放在系统PATH环境变量中的目录
- 或者：放在Chrome浏览器安装目录

### 4. 验证安装

安装完成后，再次运行脚本：

```
python register_bot.py
```

## 常见问题解决

### 问题1：ChromeDriver版本不匹配

**症状**：运行时出现版本不匹配错误
**解决**：下载与Chrome浏览器完全匹配的ChromeDriver版本

### 问题2：网络连接问题

**症状**：虽然测试显示网站可访问，但ChromeDriver无法连接
**解决**：确保您的网络环境允许ChromeDriver访问互联网

### 问题3：权限问题

**症状**：无法运行ChromeDriver
**解决**：确保您有足够的权限运行chromedriver.exe文件

## 脚本功能说明

1. **自动测试网站连接**：脚本会自动测试临时邮箱和注册网站的可访问性
2. **智能查找ChromeDriver**：尝试在多个位置查找已安装的ChromeDriver
3. **详细错误日志**：所有操作都会记录到`register.log`文件中
4. **结果保存**：注册结果会保存在`results.md`文件中

## 运行环境要求

- Python 3.x
- Google Chrome浏览器
- 已安装的依赖包（见requirements.txt）
- 匹配版本的ChromeDriver

## 联系方式

如有问题，请联系技术支持。