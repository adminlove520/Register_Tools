import time
import random
import re
import logging
import requests
import os
import math
import string
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import json

def copy_api_key(driver):
    """
    复制API key的函数，专门处理SVG复制按钮
    
    参数:
        driver: Selenium WebDriver实例
    
    返回:
        bool: 复制是否成功
    """
    logging.info("开始尝试复制API key")
    
    # 定义多种定位方式，优先尝试常规方法，然后是特殊的SVG定位方法
    copy_button_locators = [
        # 方法1: 直接定位img标签（最优先，因为用户提供的是img标签）
        (By.XPATH, "//img[@src='/image/personal/copy.svg']"),
        # 方法2: 带有aria-describedby属性的img标签
        (By.XPATH, "//img[contains(@src, 'copy.svg') and @aria-describedby]")
    ]
    
    # 如果需要处理直接嵌入的SVG标签，使用以下特殊定位方式（根据CSDN博客）
    svg_locators = [
        # 方法3: 使用name()函数定位SVG元素（如果是内联SVG）
        (By.XPATH, "//*[name()='svg']"),
        # 方法4: 查找可能包含SVG的父元素
        (By.XPATH, "//div[contains(@class, 'copy') or contains(@class, 'apikey')]//*[name()='svg']"),
        # 方法5: 查找可能包含复制按钮的区域
        (By.XPATH, "//*[contains(@class, 'copy-button') or contains(@id, 'copy')]//*[name()='svg']")
    ]
    
    # 尝试所有定位方式
    all_locators = copy_button_locators + svg_locators
    
    for i, (by, value) in enumerate(all_locators):
        try:
            logging.info(f"尝试定位复制按钮 (方式 {i+1}/{len(all_locators)}): {by}={value}")
            
            # 查找元素
            copy_buttons = driver.find_elements(by, value)
            if copy_buttons:
                copy_button = copy_buttons[0]
                
                # 滚动到元素可见
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", copy_button)
                time.sleep(1)
                
                # 尝试标准点击
                try:
                    if copy_button.is_displayed() and copy_button.is_enabled():
                        copy_button.click()
                        logging.info(f"通过标准方法点击复制按钮 (方式 {i+1})")
                        # 等待复制操作完成
                        time.sleep(1)
                        return True
                except Exception:
                    logging.warning(f"标准点击失败，尝试JavaScript点击 (方式 {i+1})")
                
                # 尝试JavaScript点击
                try:
                    driver.execute_script("arguments[0].click();", copy_button)
                    logging.info(f"通过JavaScript点击复制按钮 (方式 {i+1})")
                    # 等待复制操作完成
                    time.sleep(1)
                    return True
                except Exception:
                    logging.warning(f"JavaScript点击失败 (方式 {i+1})")
        except Exception as e:
            logging.warning(f"定位或点击复制按钮失败 (方式 {i+1}): {e}")
    
    # 如果所有直接点击都失败，尝试通过JavaScript触发复制事件
    try:
        logging.info("所有直接点击方式失败，尝试通过JavaScript触发复制事件")
        
        # 查找可能包含API key的元素
        api_key_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'api-key') or contains(@id, 'api-key') or contains(@data-testid, 'api-key')]")
        if api_key_elements:
            api_key_element = api_key_elements[0]
            api_key = api_key_element.text.strip()
            
            # 创建临时元素来复制文本
            driver.execute_script("""
                var tempInput = document.createElement('input');
                tempInput.value = arguments[0];
                document.body.appendChild(tempInput);
                tempInput.select();
                document.execCommand('copy');
                document.body.removeChild(tempInput);
                return true;
            """, api_key)
            
            logging.info(f"成功通过JavaScript复制API key: {api_key[:8]}...")
            return True
    except Exception as e:
        logging.error(f"通过JavaScript触发复制事件失败: {e}")
    
    logging.error("无法复制API key，所有方法都失败了")
    return False

# 配置日志
import sys

# 修复Unicode编码问题
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if hasattr(stream, 'buffer'):
                stream.buffer.write(msg.encode('utf-8') + b'\n')
            else:
                stream.write(msg + '\n')
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("register.log", encoding='utf-8'),
        UnicodeStreamHandler(sys.stdout)
    ]
)

# 生成4位随机英文字母
def generate_random_letters():
    return ''.join(random.choices(string.ascii_letters, k=4))

# 生成随机中文昵称（符合4-16字符要求，看起来像正常用户）
def generate_chinese_name():
    # 常用中文名组合
    surnames = ['王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴', '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗']
    
    # 常用中文名字字符
    common_characters = [
        '明', '华', '强', '丽', '敏', '静', '磊', '军', '洋', '勇', 
        '艳', '杰', '娟', '涛', '辉', '梅', '超', '秀', '霞', '永', 
        '芳', '庆', '辉', '健', '英', '浩', '林', '丹', '宇', '宁',
        '梦', '雪', '欣', '佳', '雨', '思', '瑞', '阳', '轩', '子'
    ]
    
    # 选择一个姓氏
    surname = random.choice(surnames)
    
    # 选择2-15个常用字作为名字部分（使总长度在3-16之间）
    name_length = random.randint(2, 15)
    given_name = ''.join(random.choices(common_characters, k=name_length))
    
    # 组合成完整的中文名
    full_name = surname + given_name
    
    # 确保最终长度在4-16字符之间
    while len(full_name) < 4 or len(full_name) > 16:
        if len(full_name) < 4:
            full_name += random.choice(common_characters)
        else:
            full_name = full_name[:16]
    
    return full_name

# 生成符合要求的密码（8-30字符，必须包含大小写字母、数字和特殊字符）
def generate_password():
    # 定义字符集
    lower_chars = 'abcdefghijklmnopqrstuvwxyz'
    upper_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    digit_chars = '0123456789'
    special_chars = '~!@#$%^'
    
    # 选择密码长度（8-30）
    length = random.randint(10, 20)  # 选择一个合理的长度范围
    
    # 确保包含每种类型的字符
    password = [
        random.choice(lower_chars),
        random.choice(upper_chars),
        random.choice(digit_chars),
        random.choice(special_chars)
    ]
    
    # 剩余位置随机填充所有类型的字符
    all_chars = lower_chars + upper_chars + digit_chars + special_chars
    password.extend(random.choices(all_chars, k=length-4))
    
    # 打乱密码字符顺序
    random.shuffle(password)
    
    # 组合成最终密码
    return ''.join(password)

def test_network_connection(url, timeout=10):
    """测试网络连接"""
    logging.info(f"测试网络连接: {url}")
    try:
        # 不验证SSL证书，添加User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=timeout, verify=False, headers=headers)
        logging.info(f"连接测试成功: {url}, 状态码: {response.status_code}")
        return True, response.status_code
    except requests.exceptions.ConnectionError as e:
        logging.error(f"连接错误: {url}, 错误: {str(e)}")
        return False, f"连接错误: {str(e)}"
    except requests.exceptions.Timeout as e:
        logging.error(f"连接超时: {url}, 错误: {str(e)}")
        return False, f"超时错误: {str(e)}"
    except Exception as e:
        logging.error(f"网络测试异常: {url}, 错误: {str(e)}")
        return False, f"异常: {str(e)}"

# 获取临时邮箱
def get_temp_email(driver):
    # 先测试网络连接
    email_site = 'http://mail0.dfyx.xyz/'
    connected, status = test_network_connection(email_site)
    if not connected:
        logging.error(f"无法连接到临时邮箱网站: {status}")
        return None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 打开临时邮箱网站
            logging.info(f"尝试访问临时邮箱网站 (尝试 {attempt+1}/{max_retries})\n")
            driver.set_page_load_timeout(30)
            driver.get(email_site)
            
            # 等待页面加载完成
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(2)
            
            # 尝试多种方式点击刷新按钮
            refresh_clicked = False
            try:
                # 方式1: 通过ID查找
                refresh_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, 'refreshShortid'))
                )
                refresh_button.click()
                logging.info("成功点击刷新按钮 (通过ID)")
                refresh_clicked = True
            except Exception as e:
                logging.warning(f"通过ID点击刷新按钮失败: {e}")
                try:
                    # 方式2: 通过其他选择器查找
                    refresh_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@id, 'refresh')]"))
                    )
                    refresh_button.click()
                    logging.info("成功点击刷新按钮 (通过XPATH)")
                    refresh_clicked = True
                except Exception as e2:
                    logging.error(f"通过XPATH点击刷新按钮也失败: {e2}")
            
            if refresh_clicked:
                time.sleep(2)
            
            # 尝试多种方式获取邮箱地址
            # 方式1: 查找包含邮箱的按钮或文本元素
            email_elements = driver.find_elements(By.XPATH, "//button | //div | //span")
            for element in email_elements:
                try:
                    text = element.text.strip()
                    if '@' in text and len(text) > 5:
                        # 提取邮箱格式文本
                        email_match = re.search(r'\S+@\S+', text)
                        if email_match:
                            email = email_match.group(0)
                            logging.info(f"成功获取邮箱地址: {email}")
                            return email
                except Exception:
                    continue
            
            # 方式2: 查找特定class的元素
            email_containers = driver.find_elements(By.CLASS_NAME, 'ui')
            for container in email_containers:
                try:
                    text = container.text.strip()
                    if '@' in text:
                        email_parts = re.findall(r'\S+@\S+', text)
                        if email_parts:
                            email = email_parts[0]
                            logging.info(f"成功获取邮箱地址: {email}")
                            return email
                except Exception:
                    continue
            
            # 方式3: 直接从页面源码中提取
            page_source = driver.page_source
            email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_source)
            if email_matches:
                for potential_email in email_matches:
                    if len(potential_email) > 5:
                        logging.info(f"从页面源码中提取到邮箱地址: {potential_email}")
                        return potential_email
            
            logging.warning(f"尝试 {attempt+1}/{max_retries} 次后仍未获取到邮箱地址")
            time.sleep(3)
            
        except Exception as e:
            logging.error(f"获取临时邮箱时出错: {e}")
            time.sleep(3)
    
    logging.error("达到最大重试次数，无法获取临时邮箱")
    return None

# 处理滑动验证
def handle_slider_verification(driver):
    """
    增强版滑动验证处理，特别优化了puzzle-captcha类型验证码的识别和通过能力
    基于用户提供的CSS结构进行专门优化，采用更接近人类的拖动策略
    """
    import time
    import random
    import math
    logging.info("开始处理滑动验证...")
    
    # 优先检查是否是puzzle-captcha类型
    is_puzzle_captcha = False
    puzzle_container = None
    
    try:
        puzzle_container = driver.find_element(By.CSS_SELECTOR, '.puzzle-captcha-body')
        if puzzle_container and puzzle_container.is_displayed():
            is_puzzle_captcha = True
            logging.info("检测到puzzle-captcha类型的验证码，使用专门优化的处理逻辑")
    except Exception:
        logging.info("未检测到puzzle-captcha类型，使用通用滑动验证处理")
    
    # 增强的滑块定位策略列表，优先puzzle-captcha相关定位器
    slider_locators = []
    
    if is_puzzle_captcha:
        # puzzle-captcha 特定定位器，根据用户提供的CSS结构优化
        slider_locators = [
            (By.CSS_SELECTOR, '.puzzle-captcha-body .slider'),
            (By.CSS_SELECTOR, '.puzzle-captcha-body .slider-wrap .slider'),
            (By.CSS_SELECTOR, '.puzzle-captcha-center .slider'),
            (By.CSS_SELECTOR, '.slider-wrap .slider'),
            (By.XPATH, "//div[@class='puzzle-captcha-body']//div[contains(@class, 'slider')]"),
            (By.XPATH, "//div[contains(@class, 'puzzle-captcha')]//div[contains(@class, 'slider')]"),
            (By.CSS_SELECTOR, '.slider'),  # 通用后备
        ]
    else:
        # 通用滑动验证定位器
        slider_locators = [
            # reCAPTCHA V2 特定定位器
            (By.CSS_SELECTOR, '.rc-slider'),
            (By.CSS_SELECTOR, '.rc-slider-handle'),
            (By.CSS_SELECTOR, '.recaptcha-checkbox-border'),
            (By.CSS_SELECTOR, '.recaptcha-checkbox-spinner'),
            (By.XPATH, "//*[@id='recaptcha-verify-button']"),
            
            # 常见滑动验证类名
            (By.CSS_SELECTOR, '.slider'),
            (By.CSS_SELECTOR, '.geetest_slider_button'),
            (By.CSS_SELECTOR, '.captcha-slider'),
            (By.CSS_SELECTOR, '.slider-btn'),
            (By.CSS_SELECTOR, '.drag-handle'),
            (By.CSS_SELECTOR, '.nc_iconfont.btn_slide'),
            (By.CSS_SELECTOR, '.tcaptcha-drag-button'),
            
            # XPath模糊匹配
            (By.XPATH, "//div[contains(@class, 'slider')]"),
            (By.XPATH, "//div[contains(@class, 'drag')]"),
            (By.XPATH, "//div[contains(@class, 'move')]"),
        ]
    
    slider = None
    found_in_iframe = False
    
    # 1. 先在主页面查找滑块
    for locator_type, locator_value in slider_locators:
        try:
            slider = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((locator_type, locator_value)))
            logging.info(f"找到滑动验证元素: {locator_type}={locator_value}")
            break
        except Exception:
            continue
    
    # 2. 如果主页面没找到，尝试在所有iframe中查找
    if not slider:
        try:
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            logging.info(f"找到{len(iframes)}个iframe，开始在其中查找滑块...")
            
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    logging.info(f"在iframe[{i}]中查找滑块...")
                    
                    # 在iframe中尝试所有定位策略
                    for locator_type, locator_value in slider_locators:
                        try:
                            slider = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((locator_type, locator_value)))
                            logging.info(f"在iframe[{i}]中找到滑动验证: {locator_type}={locator_value}")
                            found_in_iframe = True
                            break
                        except Exception:
                            continue
                    
                    if slider:
                        break
                    
                    driver.switch_to.default_content()
                except Exception as e:
                    logging.warning(f"切换到iframe[{i}]时出错: {e}")
                    driver.switch_to.default_content()
                    continue
        except Exception as e:
            logging.warning(f"查找iframe时出错: {e}")
    
    if slider:
        try:
            # 等待滑块完全加载
            WebDriverWait(driver, 3).until(lambda d: slider.is_displayed() and slider.is_enabled())
            
            # 滚动到滑块可见，确保用户能看到
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", slider)
            time.sleep(random.uniform(0.8, 1.2))  # 增加等待时间，让页面完全稳定
            
            # 获取滑块位置和尺寸
            slider_location = slider.location
            slider_size = slider.size
            logging.info(f"滑块位置: {slider_location}, 尺寸: {slider_size}")
            
            # 尝试多种方式确定拖动距离
            drag_distance = None
            
            # 针对puzzle-captcha类型的特定优化计算
            if is_puzzle_captcha:
                # 使用增强版JavaScript动态分析缺口位置
                try:
                    logging.info("使用增强版JavaScript动态分析puzzle-captcha缺口位置")
                    
                    # 执行专门为puzzle-captcha优化的JavaScript
                    drag_distance = driver.execute_script('''
                        // 专门针对.puzzle-captcha-body优化的缺口分析函数
                        function getGapPosition() {
                            const puzzleBody = document.querySelector('.puzzle-captcha-body');
                            if (!puzzleBody) return null;
                            
                            // 方法1: 直接从CSS变量获取缺口位置（如果网站使用）
                            const style = getComputedStyle(puzzleBody);
                            const gapPos = style.getPropertyValue('--gap-position') || 
                                          style.getPropertyValue('--target-offset');
                            if (gapPos && !isNaN(parseFloat(gapPos))) {
                                return parseFloat(gapPos);
                            }
                            
                            // 方法2: 分析缺口元素的精确位置
                            const gapElement = document.querySelector('.puzzle-captcha-body .gap') ||
                                              document.querySelector('.puzzle-captcha-body .target') ||
                                              document.querySelector('.puzzle-captcha-body [class*="gap"]');
                            
                            if (gapElement) {
                                // 获取元素的computed style
                                const gapStyle = getComputedStyle(gapElement);
                                
                                // 优先检查left属性
                                const left = parseFloat(gapStyle.left);
                                if (!isNaN(left) && left > 0) {
                                    return left;
                                }
                                
                                // 检查transform属性（最关键的一步）
                                const transform = gapStyle.transform;
                                if (transform && transform !== 'none') {
                                    // 使用正确的正则表达式匹配translateX值
                                        const match = transform.match(/translateX\\(([^)]+)\\)/);
                                    if (match && match[1]) {
                                        const translateX = parseFloat(match[1]);
                                        if (!isNaN(translateX) && translateX > 0) {
                                            return translateX;
                                        }
                                    }
                                }
                                
                                // 获取元素的getBoundingClientRect()作为备选
                                const rect = gapElement.getBoundingClientRect();
                                return rect.left;
                            }
                            
                            // 方法3: 分析滑块轨道的宽度（更准确的方法）
                            const sliderTrack = document.querySelector('.puzzle-captcha-body .slider-path') ||
                                              document.querySelector('.puzzle-captcha-body .slider-track');
                            
                            const sliderWrap = document.querySelector('.puzzle-captcha-body .slider-wrap');
                            
                            if (sliderTrack) {
                                const trackRect = sliderTrack.getBoundingClientRect();
                                return trackRect.width * 0.75; // 通常缺口位置在轨道宽度的75%左右
                            } else if (sliderWrap) {
                                const wrapRect = sliderWrap.getBoundingClientRect();
                                return wrapRect.width * 0.7; // 滑块容器宽度的70%左右
                            }
                            
                            // 方法4: 分析背景图和滑块的关系
                            const bgElement = document.querySelector('.puzzle-captcha-body .bg');
                            if (bgElement) {
                                const bgRect = bgElement.getBoundingClientRect();
                                // 通常拖动距离是背景图宽度减去滑块宽度的70-80%
                                return bgRect.width * (0.7 + Math.random() * 0.1);
                            }
                            
                            // 方法5: 作为最后的备选方案，使用经验值
                            return 200 + Math.random() * 80; // 标准puzzle-captcha的常见范围
                        }
                        
                        return getGapPosition();
                    ''')
                    
                    if drag_distance and drag_distance > 0:
                                # 添加适量随机性，但保持在合理范围内
                                drag_distance = drag_distance * random.uniform(0.95, 1.05) - random.uniform(5, 15)
                                drag_distance = max(100, min(drag_distance, 280))  # 确保在有效范围内
                                logging.info(f"通过JavaScript分析得到puzzle-captcha拖动距离: {drag_distance:.2f}px")
                    else:
                        # 备选方案：使用滑块轨道宽度计算
                        try:
                            slider_track = driver.find_element(By.CSS_SELECTOR, '.puzzle-captcha-body .slider-path')
                            if slider_track:
                                track_size = slider_track.size
                                drag_distance = track_size['width'] * 0.75  # 75%的轨道宽度通常是正确的拖动距离
                                logging.info(f"使用轨道宽度计算拖动距离: {drag_distance}px")
                        except Exception:
                            logging.warning("无法获取轨道元素，使用默认值")
                except Exception as e:
                    logging.warning(f"JavaScript分析puzzle-captcha缺口位置失败: {e}")
            
            # 如果没有获取到精确的拖动距离，使用通用方法
            if drag_distance is None:
                try:
                    # 查找轨道元素
                    track_locators = [
                        (By.CSS_SELECTOR, '.slider-path'),
                        (By.CSS_SELECTOR, '.slider-track'),
                        (By.CSS_SELECTOR, '.slider-container'),
                        (By.CSS_SELECTOR, '.captcha-container'),
                        (By.XPATH, "//div[contains(@class, 'track')]")
                    ]
                    
                    for locator_type, locator_value in track_locators:
                        try:
                            track = driver.find_element(locator_type, locator_value)
                            track_size = track.size
                            drag_distance = track_size['width'] * 0.8  # 80%的轨道宽度
                            logging.info(f"通过轨道计算拖动距离: {drag_distance}px")
                            break
                        except Exception:
                            continue
                except Exception:
                    pass
            
            # 使用默认值作为最后备选
            if drag_distance is None:
                drag_distance = random.uniform(180, 260)
                logging.info(f"使用默认拖动距离: {drag_distance}px")
            
            # 确保拖动距离在有效范围内
            drag_distance = max(100, min(drag_distance, 300))
            
            # 创建人类拖动路径生成器 - 全新优化版本
            def generate_human_motion_path(target_distance):
                """
                生成更接近人类操作的拖动路径，基于心理学研究的人类运动模型
                包含加速-匀速-减速阶段，以及微小的不规则性
                """
                path = []
                current_distance = 0
                
                # 根据目标距离调整总时间
                total_time = 0.8 + (target_distance / 300) * 1.5  # 距离越长，时间越长
                
                # 确定实际目标距离，添加微小偏差避免被检测
                actual_target = target_distance * random.uniform(0.95, 1.02)
                
                # 计算各阶段距离比例
                acceleration_ratio = random.uniform(0.35, 0.45)  # 加速阶段占比
                uniform_ratio = random.uniform(0.2, 0.3)  # 匀速阶段占比
                deceleration_ratio = 1.0 - acceleration_ratio - uniform_ratio  # 减速阶段占比
                
                # 计算各阶段距离
                acceleration_distance = actual_target * acceleration_ratio
                uniform_distance = actual_target * uniform_ratio
                deceleration_distance = actual_target * deceleration_ratio
                
                # 阶段1: 初始准备阶段 - 轻微的上下晃动
                start_jitters = random.randint(1, 3)
                for _ in range(start_jitters):
                    y_offset = random.uniform(-1.0, 1.0)
                    path.append((0, y_offset))
                    time.sleep(random.uniform(0.05, 0.1))
                
                # 阶段2: 加速阶段 - 使用平滑的正弦曲线
                acceleration_steps = random.randint(4, 6)
                for i in range(acceleration_steps):
                    progress = (i + 1) / acceleration_steps
                    # 使用正弦函数实现平滑加速
                    acceleration_factor = (1 - math.cos(progress * math.pi / 2)) * 0.5
                    step = acceleration_distance * acceleration_factor * random.uniform(0.9, 1.1)
                    
                    if step > 0 and current_distance + step <= actual_target:
                        current_distance += step
                        # 加速阶段的y轴偏移较小
                        y_offset = random.uniform(-0.6, 0.6) * (1 - progress)
                        path.append((step, y_offset))
                    
                    if current_distance >= actual_target:
                        break
                
                # 阶段3: 匀速阶段 - 稳定但有微小波动
                if current_distance < actual_target:
                    uniform_steps = random.randint(3, 5)
                    uniform_step_size = uniform_distance / uniform_steps
                    
                    for i in range(uniform_steps):
                        # 匀速阶段的速度有小幅波动
                        step = uniform_step_size * random.uniform(0.9, 1.1)
                        
                        if step > 0 and current_distance + step <= actual_target:
                            current_distance += step
                            # 匀速阶段有中等程度的y轴偏移
                            y_offset = random.uniform(-0.8, 0.8)
                            path.append((step, y_offset))
                        
                        if current_distance >= actual_target:
                            break
                
                # 阶段4: 减速阶段 - 使用余弦曲线实现平滑减速
                if current_distance < actual_target:
                    remaining_distance = actual_target - current_distance
                    deceleration_steps = random.randint(4, 6)
                    
                    for i in range(deceleration_steps):
                        progress = (i + 1) / deceleration_steps
                        # 使用余弦函数实现平滑减速
                        deceleration_factor = (1 + math.cos(progress * math.pi / 2)) * 0.5
                        step = remaining_distance * deceleration_factor * random.uniform(0.9, 1.1)
                        
                        if step > 0 and current_distance + step <= actual_target:
                            current_distance += step
                            # 减速阶段的y轴偏移逐渐增大
                            y_offset = random.uniform(-1.2, 1.2) * progress
                            path.append((step, y_offset))
                        
                        if current_distance >= actual_target:
                            break
                
                # 阶段5: 微调阶段 - 接近目标时的小幅度调整
                if current_distance < actual_target:
                    remaining = actual_target - current_distance
                    # 只添加一个精确的微调步骤
                    path.append((remaining, random.uniform(-0.5, 0.5)))
                
                return path
            
            # 执行人类风格的滑动操作
            def perform_human_slide(actions, slider, path, total_time):
                """
                以人类方式执行滑动操作，包含犹豫、停顿和不规则性
                """
                # 计算每步的基础时间间隔
                interval_time = total_time / len(path) if path else 0.1
                
                # 分批执行，每批处理2-4个步骤
                batch_size = random.randint(2, 4)
                
                for i in range(0, len(path), batch_size):
                    batch = path[i:i+batch_size]
                    batch_actions = ActionChains(driver)
                    
                    for step_x, step_y in batch:
                        # 限制单次最大移动距离
                        if abs(step_x) > 40:
                            step_x = 40 if step_x > 0 else -40
                        batch_actions.move_by_offset(step_x, step_y)
                    
                    # 随机添加微小的延迟变化
                    batch_time = interval_time * len(batch) * random.uniform(0.9, 1.1)
                    
                    # 执行这一批动作
                    batch_actions.perform()
                    
                    # 批次之间添加随机停顿
                    time.sleep(random.uniform(0.03, 0.12))
                
                # 接近终点时的特殊处理 - 更符合人类行为
                if random.random() < 0.7:  # 70%的概率执行微调
                    # 微小的左右调整来模拟人类对准
                    for _ in range(random.randint(2, 4)):
                        adjust_x = random.uniform(-0.8, 0.8)
                        adjust_y = random.uniform(-0.8, 0.8)
                        actions.move_by_offset(adjust_x, adjust_y).perform()
                        time.sleep(random.uniform(0.04, 0.08))
            
            # 执行滑动操作
            actions = ActionChains(driver)
            
            # 1. 模拟人类移动到滑块的过程
            try:
                # 先移动到滑块附近的随机位置
                initial_offset_x = random.randint(-30, 30)
                initial_offset_y = random.randint(-20, 20)
                
                # 使用更精确的位置计算
                current_scroll_x = driver.execute_script('return window.pageXOffset;')
                current_scroll_y = driver.execute_script('return window.pageYOffset;')
                
                # 移动到滑块附近
                target_x = slider.location['x'] + slider.size['width'] / 2 - current_scroll_x + initial_offset_x
                target_y = slider.location['y'] + slider.size['height'] / 2 - current_scroll_y + initial_offset_y
                
                # 分两步移动，更自然
                actions.move_by_offset(target_x * 0.7, target_y * 0.7).perform()
                time.sleep(random.uniform(0.2, 0.4))
                
                actions.move_by_offset(target_x * 0.3, target_y * 0.3).perform()
                time.sleep(random.uniform(0.3, 0.7))  # 停留观察时间
                
                # 2. 模拟人类犹豫行为
                if random.random() < 0.8:  # 80%的概率出现犹豫
                    hesitation_x = random.uniform(-4, 4)
                    hesitation_y = random.uniform(-4, 4)
                    actions.move_by_offset(hesitation_x, hesitation_y).perform()
                    time.sleep(random.uniform(0.1, 0.3))
                    actions.move_by_offset(-hesitation_x, -hesitation_y).perform()
                    time.sleep(random.uniform(0.2, 0.5))
                
                # 3. 先等待用户手动操作，1分钟超时后再自动处理
                user_interacted = False
                skip_auto_drag = False  # 初始化变量，默认为不跳过自动拖动
                try:
                    logging.info("等待用户手动拖动滑块... (60秒超时后将自动处理)")
                    
                    # 获取滑块初始位置
                    initial_location = slider.location
                    
                    # 设置1分钟超时等待滑块位置变化
                    start_time = time.time()
                    timeout = 60  # 60秒超时
                    
                    while time.time() - start_time < timeout:
                        # 检查滑块位置是否发生变化
                        current_location = slider.location
                        # 如果x坐标变化超过5像素，认为用户已手动操作
                        if abs(current_location['x'] - initial_location['x']) > 5:
                            logging.info("检测到用户手动操作，取消自动拖动")
                            user_interacted = True
                            break
                        
                        # 短暂休眠以减少CPU使用
                        time.sleep(0.5)
                        
                        # 刷新滑块引用以避免过期
                        try:
                            slider = driver.find_element(By.CSS_SELECTOR, slider.find_element(By.XPATH, './..').get_attribute('css selector'))
                        except:
                            pass
                    
                    if user_interacted:
                        # 设置一个标志来跳过自动拖动逻辑
                        skip_auto_drag = True
                        logging.info("用户已手动操作，准备检查验证结果")
                    else:
                        logging.info("用户未操作，开始自动拖动滑块")
                        skip_auto_drag = False
                except Exception as wait_error:
                    logging.warning(f"等待用户操作时出错: {wait_error}，将继续自动处理")
                    skip_auto_drag = False  # 出错时默认执行自动拖动
                
                # 3. 如果用户已手动操作，跳过自动拖动
                if skip_auto_drag:
                    # 直接检查验证结果并立即返回，不再等待
                    logging.info("用户手动操作成功，立即返回继续流程")
                    return True  # 假设用户手动操作成功
                    
                # 3. 点击并按住
                actions.click_and_hold(slider).perform()
                logging.info("开始拖动滑块")
                time.sleep(random.uniform(0.1, 0.3))  # 按住后的短暂停顿
                
                # 4. 生成并执行人类风格的拖动路径
                human_path = generate_human_motion_path(drag_distance)
                total_drag_time = random.uniform(1.2, 2.2)  # 拖动总时间
                
                # 执行拖动路径
                perform_human_slide(actions, slider, human_path, total_drag_time)
                
                # 5. 释放前的停顿，模拟确认位置
                time.sleep(random.uniform(0.3, 0.6))
                actions.release().perform()
                logging.info("完成滑块拖动")
                
                # 6. 等待验证完成
                time.sleep(random.uniform(2.0, 3.0))  # 增加等待时间，确保验证完全完成
                
            except Exception as e:
                logging.error(f"执行滑块拖动操作时出错: {e}")
                # 尝试简单的拖动作为后备
                try:
                    actions.click_and_hold(slider).perform()
                    time.sleep(0.2)
                    actions.move_by_offset(drag_distance * 0.8, 0).perform()
                    time.sleep(0.3)
                    actions.move_by_offset(drag_distance * 0.2, 0).perform()
                    time.sleep(0.5)
                    actions.release().perform()
                    logging.info("执行了后备拖动策略")
                except Exception:
                    logging.error("后备拖动策略也失败了")
            
            # 验证成功检查 - 增强版
            def check_verification_success():
                """
                全面检查验证是否成功，包含多种验证方法
                """
                # 1. 等待验证结果稳定
                time.sleep(1.0)
                
                # 2. 检查puzzle-captcha特定的成功标志
                if is_puzzle_captcha:
                    try:
                        # 检查成功提示
                        success_elements = driver.find_elements(By.CSS_SELECTOR, 
                            '.puzzle-captcha-body .success, ' +
                            '.puzzle-captcha-body .verified, ' +
                            '.puzzle-captcha-body [class*="success"], ' +
                            '.puzzle-captcha-body [style*="display: none"] .slider-path'  # 滑块轨道隐藏
                        )
                        
                        for elem in success_elements:
                            if elem.is_displayed():
                                logging.info("检测到puzzle-captcha验证成功标志")
                                return True
                        
                        # 检查是否出现了新的元素或类名变化
                        new_container = driver.find_element(By.CSS_SELECTOR, '.puzzle-captcha-body')
                        new_classes = new_container.get_attribute('class')
                        if 'success' in new_classes or 'verified' in new_classes:
                            logging.info("检测到验证码容器类名变化，表示成功")
                            return True
                    except Exception:
                        pass
                
                # 3. 检查通用成功选择器
                success_selectors = [
                    '.success', '.verified', '.valid', '.passed',
                    '.captcha-success', '.recaptcha-success',
                    '.result-tip:not(.error)', '.result-tip:not(.fail)',
                    '[aria-checked="true"]', '[data-status="success"]'
                ]
                
                for selector in success_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.size['width'] > 10:
                                logging.info(f"检测到成功元素: {selector}")
                                return True
                    except Exception:
                        pass
                
                # 4. 检查成功文本提示
                success_texts = ['成功', '验证通过', '验证成功', 'success', 'verified', 'passed', '完成']
                for text in success_texts:
                    try:
                        elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
                        for elem in elements:
                            if elem.is_displayed():
                                logging.info(f"检测到成功文本: {text}")
                                return True
                    except Exception:
                        pass
                
                # 5. 检查滑块是否消失或不可见
                try:
                    if not slider.is_displayed():
                        logging.info("滑块元素已不可见，验证可能成功")
                        return True
                except Exception:
                    # 如果元素已经不存在，也可能是验证成功
                    logging.info("滑块元素已不存在，验证可能成功")
                    return True
                
                # 6. 检查滑块位置是否变化（移动到了右侧）
                try:
                    new_location = slider.location
                    if new_location['x'] > slider_location['x'] + drag_distance * 0.7:
                        logging.info("滑块已明显移动，验证可能成功")
                        return True
                except Exception:
                    pass
                
                return False
            
            # 检查验证是否成功
            if check_verification_success():
                logging.info("滑动验证成功通过")
                # 如果在iframe中，切回主页面
                if found_in_iframe:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                
                # 滑动验证成功后检查临时邮箱情况
                logging.info("开始检查临时邮箱情况...")
                try:
                    # 保存当前窗口
                    main_window = driver.current_window_handle
                    
                    # 切换到邮箱标签页（如果存在）
                    found_email_tab = False
                    for handle in driver.window_handles:
                        driver.switch_to.window(handle)
                        if 'mail0.dfyx.xyz' in driver.current_url:
                            found_email_tab = True
                            logging.info("已切换到邮箱标签页")
                            break
                    
                    # 如果没有找到邮箱标签页，打开一个新的
                    if not found_email_tab:
                        logging.info("未找到邮箱标签页，打开新标签页访问邮箱")
                        driver.execute_script("window.open('http://mail0.dfyx.xyz/');")
                        driver.switch_to.window(driver.window_handles[-1])
                    
                    # 刷新邮箱页面检查新邮件
                    driver.refresh()
                    logging.info("已刷新邮箱页面，等待邮件到达")
                    time.sleep(20)  # 给邮件一些时间到达
                    
                    # 切换回主窗口
                    driver.switch_to.window(main_window)
                    logging.info("已切回主窗口")
                except Exception as e:
                    logging.error(f"检查临时邮箱时出错: {e}")
                    # 确保切换回主窗口
                    try:
                        driver.switch_to.window(main_window)
                    except:
                        pass
                
                return True
            else:
                logging.warning("滑动验证可能未通过，尝试重新验证")
                # 等待一段时间后重试
                time.sleep(random.uniform(1.0, 2.0))
                
                # 如果是puzzle-captcha类型，可以尝试重新拖动
                if is_puzzle_captcha:
                    logging.info("尝试第二次拖动")
                    return handle_slider_verification(driver)  # 递归调用重试
                    
        except Exception as e:
            logging.error(f"处理滑动验证时发生错误: {e}")
    else:
        logging.warning("未找到滑块验证元素")
    
    # 如果在iframe中，切回主页面
    if found_in_iframe:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
    
    return False

# 辅助函数：检查验证码发送成功提示
def check_success_message(driver):
    # """检查是否有验证码发送成功的提示或验证通过的提示"""
    # logging.info("检查验证码发送成功提示和验证通过提示...")
    # success_patterns = [
    #     "已发送", "sent", "success", "成功", "verification code sent", 
    #     "验证码已发送", "code has been sent", "发送成功", "验证码发送成功",
    #     # 添加验证通过相关的提示文本
    #     "验证通过", "验证成功", "通过验证", "Verification passed", 
    #     "Verification success", "Valid", "Verified", "Passed",
    #     "check success", "验证通过", "security check passed"
    # ]
    
    # 尝试多种方式查找成功提示
    # 1. 通过文本内容查找
    # try:
    #     for pattern in success_patterns:
    #         success_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{pattern}')]")
    #         for elem in success_elements:
    #             if elem.is_displayed() and elem.size['width'] > 0 and elem.size['height'] > 0:
    #                 logging.info(f"检测到验证码发送成功提示: {elem.text}")
    #                 return True
    # except Exception as e:
    #     logging.warning(f"检查成功提示失败: {e}")
    
    # 2. 检查是否有倒计时元素出现（通常验证码发送后会有倒计时）
    try:
        countdown_elements = driver.find_elements(By.XPATH, 
            "//*[contains(text(), '秒') or contains(text(), 's') or contains(@class, 'countdown') or contains(@id, 'countdown')]"
        )
        for elem in countdown_elements:
            if elem.is_displayed() and any(char.isdigit() for char in elem.text):
                logging.info(f"检测到验证码发送后的倒计时: {elem.text}")
                return True
    except Exception as e:
        logging.warning(f"检查倒计时元素失败: {e}")
    
    return False

# 验证码发送函数
def trigger_verification_code(driver):
    """
    触发验证码发送并处理滑块验证
    
    Args:
        driver: WebDriver实例
    
    Returns:
        bool: 是否成功触发验证码发送
    """
    import time
    logging.info("开始尝试触发验证码发送...")
    
    # 验证码输入框定位策略 - 增强版
    verification_input_locators = [
        (By.XPATH, "//div[contains(@class, 'ant-formily-item')]//input[contains(@placeholder, '请输入验证码')]")
    ]
    
    verification_input = None
    
    # 尝试定位验证码输入框
    for locator_type, locator_value in verification_input_locators:
        try:
            verification_input = WebDriverWait(driver, 8).until(EC.presence_of_element_located((locator_type, locator_value)))
            if verification_input:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((locator_type, locator_value)))
                logging.info(f"验证码输入框可交互: {locator_type}={locator_value}")
                break
        except Exception as e:
            logging.warning(f"使用定位器 {locator_type}={locator_value} 未找到验证码输入框: {e}")
    
    if not verification_input:
        logging.error("无法定位验证码输入框")
        return False
    
    # 保存当前窗口句柄
    current_window = driver.current_window_handle
    
    # 只使用父元素内ant-typography元素策略
    strategies = []
    
    try:
        # 查找父元素
        parent_element = verification_input.find_element(By.XPATH, '..')
        
        # 查找父元素内所有元素
        nearby_elements = parent_element.find_elements(By.XPATH, './/*')
        logging.info(f"在验证码输入框父元素中查找ant-typography元素")
        
        # 只查找并添加ant-typography元素
        for i, elem in enumerate(nearby_elements[:15]):
            try:
                if elem.is_displayed() and elem.is_enabled() and elem != verification_input:
                    elem_class = elem.get_attribute('class')
                    elem_text = elem.text.strip()
                    elem_tag = elem.tag_name
                    
                    if 'ant-typography' in (elem_class or ''):
                        strategies.append((elem, f"父元素内ant-typography元素 {i+1}: 标签={elem_tag}, 文本='{elem_text}'"))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"获取父元素信息失败: {e}")
    
    # 执行策略
    success = False
    for elem, strategy_name in strategies:
        try:
            logging.info(f"尝试策略: {strategy_name}")
            
            # 对找到的元素执行点击
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
            time.sleep(0.5)
            
            # 尝试点击元素
            try:
                elem.click()
                logging.info(f"成功点击元素: {strategy_name}")
            except:
                driver.execute_script("arguments[0].click();", elem)
                logging.info(f"通过JavaScript成功点击元素: {strategy_name}")
            
            time.sleep(1.5)  # 等待反馈
            
            # 处理滑块验证
            logging.info("尝试处理滑块验证...")
            handle_slider_verification(driver)
            
            # 检查成功提示
            if check_success_message(driver):
                success = True
                break
        except Exception as e:
            logging.warning(f"执行策略 {strategy_name} 时出错: {e}")
            continue
    
    # 确保切换回原始窗口
    try:
        if driver.current_window_handle != current_window:
            driver.switch_to.window(current_window)
    except Exception:
        pass
    
    logging.info(f"验证码发送触发{'成功' if success else '失败'}")
    return success

# 获取验证码
def get_verification_code(driver):
    """
    获取验证码，优化为从页面Elements中搜索DayDayMap验证码格式的6位数字
    """
    import time
    import re
    max_attempts = 10  # 减少尝试次数，避免过多等待
    email_site = 'http://mail0.dfyx.xyz/'
    
    # 确保访问正确的邮箱网站
    try:
        current_url = driver.current_url
        if email_site not in current_url:
            logging.info(f"导航到邮箱网站: {email_site}")
            driver.get(email_site)
            time.sleep(2)
    except Exception as e:
        logging.error(f"导航到邮箱网站时出错: {e}")
        driver.get(email_site)
        time.sleep(2)
    
    for attempt in range(max_attempts):
        logging.info(f"尝试获取验证码 (第 {attempt+1}/{max_attempts} 次)")
        time.sleep(5)
        
        try:
            # 不再刷新页面，直接从页面Elements中搜索
            logging.info("从页面Elements中搜索DayDayMap验证码...")
            
            # 等待页面加载完成
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except:
                pass  # 即使等待超时也继续执行
            
            # 1. 重点优化DayDayMap验证码格式的提取
            daydaymap_pattern = r'DayDayMap验证码[：:]\s*(\d{6})'
            
            # 从页面源码中提取
            page_source = driver.page_source
            code_match = re.search(daydaymap_pattern, page_source)
            if code_match:
                code = code_match.group(1)
                if len(code) == 6 and code.isdigit():
                    logging.info(f"从页面源码成功获取DayDayMap验证码: {code}")
                    return code
            
            # 2. 使用JavaScript直接在Elements中搜索包含DayDayMap验证码的元素
            try:
                logging.info("使用JavaScript在DOM Elements中搜索DayDayMap验证码元素...")
                # 查找包含'DayDayMap验证码'的所有文本节点
                elements = driver.execute_script("""
                    const results = [];
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.nodeValue.includes('DayDayMap验证码')) {
                            results.push(node.nodeValue);
                        }
                    }
                    return results;
                """)
                
                if elements:
                    for text in elements:
                        code_match = re.search(daydaymap_pattern, text)
                        if code_match:
                            code = code_match.group(1)
                            if len(code) == 6 and code.isdigit():
                                logging.info(f"通过JavaScript在Elements中找到DayDayMap验证码: {code}")
                                return code
            except Exception as e:
                logging.warning(f"JavaScript搜索元素时出错: {e}")
            
            # 3. 从可见文本中提取
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                logging.info("从页面可见文本中搜索验证码...")
                
                code_match = re.search(daydaymap_pattern, page_text)
                if code_match:
                    code = code_match.group(1)
                    if len(code) == 6 and code.isdigit():
                        logging.info(f"从可见文本成功获取DayDayMap验证码: {code}")
                        return code
            except Exception as e:
                logging.warning(f"获取页面文本时出错: {e}")
            
            # 4. 尝试其他常见格式
            other_patterns = [
                r'验证码[：:]\s*(\d{6})',  # 验证码：123456
                r'【盛邦安全】.*?[：:]\s*(\d{6})',
            ]
            
            for pattern in other_patterns:
                # 从源码尝试
                code_match = re.search(pattern, page_source)
                if code_match:
                    code = code_match.group(1)
                    if len(code) == 6 and code.isdigit() and not (code.startswith('20') and len(code) == 6):
                        logging.info(f"从页面源码成功获取验证码: {code}")
                        return code
            
            # 5. 简单的邮件点击处理（如果需要）
            try:
                logging.info("尝试定位并点击邮件列表中的验证码邮件...")
                
                # 自动点击标记
                auto_click_success = False
                
                # 首先尝试定位邮件列表表格中的盛邦安全邮件行
                email_rows = driver.find_elements(By.XPATH, "//table[@class='ui celled selectable table']//tbody[@id='maillist']//tr[contains(., '盛邦安全') and contains(., '验证码')]")
                
                if email_rows:
                    # 找到邮件行，先尝试自动点击
                    email_row = email_rows[0]
                    driver.execute_script("arguments[0].scrollIntoView(true);", email_row)
                    time.sleep(1)
                    
                    try:
                        # 尝试通过JavaScript点击
                        logging.info("尝试自动点击验证码邮件行")
                        driver.execute_script("arguments[0].click();", email_row)
                        auto_click_success = True
                        logging.info("自动点击验证码邮件行成功")
                        time.sleep(2)  # 给页面加载时间
                    except Exception as e:
                        logging.warning(f"自动点击验证码邮件行失败: {str(e)}")
                        auto_click_success = False
                    
                    # 如果自动点击失败，提示用户手动点击
                    if not auto_click_success:
                        logging.info("已定位到邮件列表中的验证码邮件行，自动点击失败，请手动点击")
                        print("请在浏览器中点击下面表格中的验证码邮件行：")
                        print("发信人: 盛邦安全 <daydaymap@webray.com.cn>")
                        print("主题: 【盛邦安全】验证码")
                        print("点击后请等待3秒钟，系统将自动提取验证码...")
                        time.sleep(3)
                else:
                    # 如果找不到精确的邮件行，尝试通用定位
                    email_elements = driver.find_elements(By.XPATH, "//div[contains(text(), '验证码') or contains(text(), 'DayDayMap')]")
                    if email_elements:
                        driver.execute_script("arguments[0].scrollIntoView(true);", email_elements[0])
                        
                        try:
                            # 尝试自动点击通用元素
                            logging.info("尝试自动点击通用验证码邮件元素")
                            driver.execute_script("arguments[0].click();", email_elements[0])
                            auto_click_success = True
                            logging.info("自动点击通用验证码邮件元素成功")
                            time.sleep(2)
                        except Exception as e:
                            logging.warning(f"自动点击通用验证码邮件元素失败: {str(e)}")
                            auto_click_success = False
                        
                        # 如果自动点击失败，提示用户手动点击
                        if not auto_click_success:
                            print("请在浏览器中点击验证码邮件")
                            print("点击后请等待3秒钟...")
                            time.sleep(3)
                    else:
                        print("未找到验证码邮件，请在邮件列表中手动查找并点击盛邦安全发送的验证码邮件")
                        time.sleep(5)
                
                # 点击后再次搜索验证码
                new_page_source = driver.page_source
                code_match = re.search(daydaymap_pattern, new_page_source)
                if code_match:
                    code = code_match.group(1)
                    if len(code) == 6 and code.isdigit():
                        logging.info(f"找到DayDayMap验证码: {code}")
                        return code
                else:
                    logging.info("未能自动提取验证码，请查看邮件并手动输入")
                    print("系统未能自动提取验证码，请查看邮件中的6位数字验证码")
            except Exception as e:
                logging.error(f"处理验证码邮件时发生错误: {str(e)}")
                pass
            
            # 6. 最后尝试直接提取所有6位数字
            try:
                logging.info("尝试直接提取所有6位数字...")
                all_digits = re.findall(r'(?<!\d)(\d{6})(?!\d)', page_source)
                if all_digits:
                    for code in reversed(all_digits):
                        if len(code) == 6 and code.isdigit() and not (code.startswith('20') and len(code) == 6):
                            logging.info(f"直接提取6位数字作为验证码: {code}")
                            return code
            except Exception:
                pass
            
            logging.info(f"第 {attempt+1} 次尝试未找到验证码，等待后重试...")
            
        except Exception as e:
            logging.error(f"获取验证码时出错: {e}")
    
    logging.error("达到最大尝试次数，无法获取验证码")
    return None

# 主注册函数
def find_chrome_driver():
    """增强版ChromeDriver查找，支持自动下载和版本管理"""
    # 常见的ChromeDriver位置
    common_paths = [
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
        os.path.join(os.getcwd(), 'chromedriver.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chromedriver.exe')
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            logging.info(f"找到ChromeDriver: {path}")
            return path
    
    # 检查PATH环境变量
    for path in os.environ['PATH'].split(os.pathsep):
        driver_path = os.path.join(path, 'chromedriver.exe')
        if os.path.exists(driver_path):
            logging.info(f"在PATH中找到ChromeDriver: {driver_path}")
            return driver_path
    
    logging.warning("未找到ChromeDriver，尝试使用webdriver_manager自动下载...")
    try:
        # 尝试使用webdriver_manager自动管理ChromeDriver
        logging.info("使用webdriver_manager获取ChromeDriver...")
        return ChromeDriverManager().install()
    except Exception as e:
        logging.error(f"webdriver_manager下载失败: {e}")
        logging.warning("请手动下载ChromeDriver并放在系统PATH或当前目录。")
        return None

def register_account():
    import time
    # 尝试查找ChromeDriver
    chrome_driver_path = find_chrome_driver()
    
    # 初始化WebDriver
    options = webdriver.ChromeOptions()
    
    # 基本配置
    options.add_argument('--start-maximized')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # 添加中文语言设置，确保浏览器以中文启动，使注册页面显示为中文
    options.add_argument('--lang=zh-CN')
    options.add_experimental_option('prefs', {
        'intl.accept_languages': 'zh-CN,zh',
        # 允许通知提醒
        'profile.default_content_setting_values.notifications': 1,
        'profile.content_settings.exceptions.notifications': {
            'mail0.dfyx.xyz': {'setting': 1}
        }
    })
    
    # 关键网络配置 - 解决连接问题
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    options.add_argument('--remote-allow-origins=*')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-features=BlockInsecurePrivateNetworkRequests')
    
    # 明确禁用代理设置
    options.add_argument('--no-proxy-server')
    options.add_argument('--proxy-bypass-list=*')
    options.add_argument('--disable-auto-reload')
    
    # 禁用代理自动检测
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 设置无代理环境变量
    options.add_argument('--disable-features=NetworkService,NetworkServiceInProcess')
    
    # 禁用连接限制
    options.add_argument('--disable-features=CrossSiteDocumentBlockingIfIsolating')
    options.add_argument('--disable-features=site-per-process')
    
    # 页面加载策略
    options.page_load_strategy = 'eager'  # 更快的页面加载策略
    
    # 禁用某些安全功能可能会有所帮助
    options.add_argument('--disable-features=site-per-process')
    options.add_argument('--disable-features=IsolateOrigins')
    
    # 设置用户配置文件以避免某些Chrome策略限制
    options.add_argument('--profile-directory=Default')
    options.add_argument('--disable-features=TranslateUI')
    
    # 添加实验性选项以解决可能的网络问题
    prefs = {
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': False,
        'safebrowsing.disable_download_protection': True,
        # 禁用代理自动检测
        'system.network.proxy.autodetect': False,
        'system.network.proxy.http_proxy': '',
        'system.network.proxy.ssl_proxy': ''
    }
    options.add_experimental_option('prefs', prefs)
    
    driver = None
    try:
        # 首先测试两个关键网站的可访问性
        email_site = 'http://mail0.dfyx.xyz/'
        register_site = 'https://www.daydaymap.com/user/register'
        
        logging.info("\n===== 网站连接测试 =====")
        email_conn, email_status = test_network_connection(email_site)
        register_conn, register_status = test_network_connection(register_site)
        
        logging.info(f"临时邮箱网站 ({email_site}): {'可访问' if email_conn else f'不可访问 - {email_status}'}")
        logging.info(f"注册网站 ({register_site}): {'可访问' if register_conn else f'不可访问 - {register_status}'}")
        
        # 初始化ChromeDriver
        try:
            # 方法1: 如果找到ChromeDriver路径，直接使用
            if chrome_driver_path:
                logging.info("使用找到的ChromeDriver路径初始化")
                driver = webdriver.Chrome(
                    service=Service(chrome_driver_path),
                    options=options
                )
            else:
                # 方法2: 尝试使用系统PATH中的ChromeDriver
                logging.info("尝试使用系统PATH中的ChromeDriver")
                driver = webdriver.Chrome(options=options)
            
            # 设置超时
            driver.set_page_load_timeout(60)
            driver.set_script_timeout(60)
            driver.implicitly_wait(10)
            
            logging.info("ChromeDriver初始化成功")
        except Exception as e:
            logging.error(f"ChromeDriver初始化失败: {str(e)}")
            logging.error("\n===== ChromeDriver错误解决指南 =====")
            logging.error("1. 请确保您已安装Google Chrome浏览器")
            logging.error("2. 下载与您Chrome浏览器版本匹配的ChromeDriver:")
            logging.error("   https://chromedriver.chromium.org/downloads")
            logging.error("3. 将chromedriver.exe放在以下任一位置:")
            logging.error("   - 当前目录 (D:/safePro/Register-tools/)")
            logging.error("   - 系统PATH环境变量中的任一目录")
            logging.error("   - 与Chrome浏览器相同的目录")
            logging.error("\n请下载ChromeDriver后重试。")
            raise
        
        # 获取临时邮箱
        email = get_temp_email(driver)
        if not email:
            raise Exception("无法获取临时邮箱")
        
        # 清晰打印获取的邮箱地址
        logging.info(f"===================================")
        logging.info(f"获取到临时邮箱: {email}")
        logging.info(f"===================================")
        
        # 打开新标签页用于注册
        driver.execute_script("window.open('about:blank');")
        driver.switch_to.window(driver.window_handles[1])
        
        # 访问注册页面
        max_attempts = 3
        register_site = 'https://www.daydaymap.com/user/register'
        # 先测试注册网站连接
        connected, status = test_network_connection(register_site)
        if not connected:
            logging.error(f"无法连接到注册网站: {status}")
            raise Exception(f"无法连接到注册网站: {status}")
            
        for attempt in range(max_attempts):
            try:
                driver.get(register_site)
                # 等待页面加载完成
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                logging.info(f"成功访问注册页面 (尝试 {attempt+1}/{max_attempts})")
                time.sleep(2)
                break
            except Exception as e:
                logging.error(f"无法访问注册页面 (尝试 {attempt+1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    logging.info("等待后重试...")
                    time.sleep(3)
                else:
                    # 尝试使用备用方式
                    try:
                        logging.info("尝试备用方式访问...")
                        driver.get('about:blank')
                        driver.execute_script(f"window.location.href = 'https://www.daydaymap.com/user/register';")
                        time.sleep(5)
                    except Exception as backup_error:
                        logging.error(f"备用方式也失败: {backup_error}")
                        raise Exception(f"无法访问注册页面: {str(e)}")
        
        # 使用邮箱前缀作为昵称，并处理确保符合要求
        email_prefix = email.split('@')[0]
        
        # 处理昵称：只保留汉字、大小写字母、下划线、数字
        # 使用正则表达式过滤不符合要求的字符
        valid_nickname = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9_]', '', email_prefix)
        
        # 确保昵称长度在4-16位之间
        if len(valid_nickname) < 4:
            # 如果太短，添加随机字母或数字
            additional_chars = 4 - len(valid_nickname)
            valid_chars = string.ascii_letters + string.digits + '_'
            valid_nickname += ''.join(random.choices(valid_chars, k=additional_chars))
            logging.info(f"昵称过短，已补充字符: {valid_nickname}")
        elif len(valid_nickname) > 16:
            # 如果太长，截断到16位
            valid_nickname = valid_nickname[:16]
            logging.info(f"昵称过长，已截断: {valid_nickname}")
        
        nickname = valid_nickname
        password = generate_password()
        
        logging.info(f"生成的昵称: {nickname}")
        logging.info(f"生成的密码: {password}")
        
        # 填写注册表单
        try:
            # 根据placeholder属性直接定位表单元素
            logging.info("开始定位并填写表单元素...")
            
            # 获取所有输入元素并进行诊断
            all_inputs = driver.find_elements(By.TAG_NAME, 'input')
            for i, element in enumerate(all_inputs):
                try:
                    attrs = {
                        'name': element.get_attribute('name'),
                        'type': element.get_attribute('type'),
                        'placeholder': element.get_attribute('placeholder'),
                        'id': element.get_attribute('id'),
                        'class': element.get_attribute('class')
                    }
                    logging.info(f"诊断：输入元素 {i+1}: {attrs}")
                except Exception as e:
                    logging.warning(f"诊断：获取元素信息失败: {e}")
            
            # 邮箱输入框 - 支持中英文placeholder
            email_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='请输入手机号或邮箱' or @placeholder='Please enter phone number or email address']")
            ))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", email_input)
            time.sleep(0.5)
            email_input.clear()
            email_input.send_keys(email)
            logging.info(f"已填写邮箱: {email}")
            print(f"获取的邮箱地址: {email}")
            
            # 昵称输入框 - 支持中英文placeholder
            nickname_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='请输入昵称' or @placeholder='Please enter nickname']")
            ))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", nickname_input)
            time.sleep(0.5)
            nickname_input.clear()
            nickname_input.send_keys(nickname)
            logging.info(f"已填写昵称: {nickname}")
            
            # 密码输入框 - 支持中英文placeholder
            password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='请输入密码' or @placeholder='Please enter password']")
            ))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", password_input)
            time.sleep(0.5)
            password_input.clear()
            password_input.send_keys(password)
            logging.info("已填写密码")
            
            # 确认密码输入框 - 支持中英文placeholder
            confirm_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='请确认密码' or @placeholder='Please confirm password']")
            ))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", confirm_password_input)
            time.sleep(0.5)
            confirm_password_input.clear()
            confirm_password_input.send_keys(password)
            logging.info("已确认密码")
            
            # 到已确认密码这里开始触发验证码发送并等待用户操作
            try:
                # 直接调用trigger_verification_code函数来点击获取验证码并处理滑块验证
                logging.info("开始触发验证码发送...")
                verification_triggered = trigger_verification_code(driver)
                
                # 无论是否触发成功，都等待10秒后直接切换到临时邮箱查看验证码
                logging.info("等待10秒后直接切换到临时邮箱查看验证码...")
                # 延时10秒后直接切换到临时邮箱
                time.sleep(10)
                
                # 直接切换回临时邮箱标签页获取验证码
                code = None
                if len(driver.window_handles) > 0:
                    driver.switch_to.window(driver.window_handles[0])
                    code = get_verification_code(driver)
                    
                    if code:
                        logging.info(f"获取到验证码: {code}")
                        # 切换回注册标签页填写验证码
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[1])
                            
                            # 填写验证码 - 改进版定位策略
                            code_input = None
                            code_locators = [
                                # 新增：更广泛的placeholder匹配
                                (By.XPATH, "//input[contains(@placeholder, '验证码') or contains(@placeholder, 'Verification') or contains(@placeholder, 'code')]"),
                                # 新增：通过类型和属性组合定位
                                (By.XPATH, "//input[@type='text'][contains(@placeholder, 'code')]"),
                                # 新增：通过表单字段名称属性
                                (By.XPATH, "//input[contains(@name, 'verification') or contains(@name, 'code')]"),
                                # 新增：通过ID属性
                                (By.XPATH, "//input[contains(@id, 'verification') or contains(@id, 'code')]"),
                                # 新增：通过class属性包含验证相关字样
                                (By.XPATH, "//input[contains(@class, 'verification') or contains(@class, 'validate')]"),
                                # 原有定位器
                                (By.NAME, 'code'),
                                (By.ID, 'code'),
                                (By.CSS_SELECTOR, "input[name='code']"),
                                (By.XPATH, "//input[contains(@class, 'code')]"),
                                # 新增：第3个输入框（通常验证码是第三个输入框）
                                (By.XPATH, "//input[3]"),
                                # 新增：第4个输入框
                                (By.XPATH, "//input[4]")
                            ]
                            for i, (by, value) in enumerate(code_locators):
                                try:
                                    logging.info(f"尝试定位验证码输入框 (方式 {i+1}/{len(code_locators)}): {by}={value}")
                                    # 先滚动到元素可见
                                    code_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((by, value)))
                                    if code_input:
                                        # 尝试滚动元素到可见区域
                                        driver.execute_script("arguments[0].scrollIntoView(true);", code_input)
                                        time.sleep(0.5)
                                        logging.info("成功定位验证码输入框")
                                        break
                                except Exception as e:
                                    logging.warning(f"定位验证码输入框失败 (方式 {i+1}): {e}")
                            
                            if code_input:
                                code_input.clear()
                                code_input.send_keys(code)
                                logging.info(f"已填写验证码: {code}")
                                
                                # 勾选同意协议 - 增强版定位策略
                                agreement_checked = False
                                agreement_locators = [
                                    # 更精确的复选框定位
                                    (By.XPATH, "//input[@type='checkbox']"),
                                    (By.XPATH, "//input[@type='checkbox']/following-sibling::span"),
                                    (By.XPATH, "//input[@type='checkbox']/preceding-sibling::span"),
                                    (By.CSS_SELECTOR, "[type='checkbox']"),
                                    # 通过标签文本查找
                                    (By.XPATH, "//label[contains(., '同意') or contains(., 'agree')]"),
                                    (By.XPATH, "//span[contains(., '同意') or contains(., 'agree')]"),
                                    (By.XPATH, "//div[contains(., '同意') or contains(., 'agree')]"),
                                    # 针对常见HTML结构的特定定位器
                                    (By.XPATH, "//span[contains(@class, 'ant-checkbox-label')]"),
                                    (By.XPATH, "//span[contains(@class, 'ant-typography') and contains(text(), '我已阅读并同意')]/parent::span"),
                                    (By.XPATH, "//span[contains(@class, 'css-zqbva3') and contains(text(), '我已阅读并同意')]/parent::span"),
                                    # 原有定位器
                                    (By.CSS_SELECTOR, '.agreement-checkbox'),
                                    (By.ID, 'agreement'),
                                    (By.XPATH, "//div[contains(@class, 'agreement')]"),
                                    (By.XPATH, "//span[contains(@class, 'checkbox')]"),
                                    (By.XPATH, "//*[contains(text(), '服务条款') or contains(text(), 'Terms')]")
                                ]
                                
                                for i, (by, value) in enumerate(agreement_locators):
                                    try:
                                        logging.info(f"尝试定位同意协议元素 (方式 {i+1}/{len(agreement_locators)}): {by}={value}")
                                        
                                        # 首先尝试找到元素
                                        agreement_elements = driver.find_elements(by, value)
                                        if agreement_elements:
                                            agreement_element = agreement_elements[0]
                                            
                                            # 先滚动到元素可见
                                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", agreement_element)
                                            time.sleep(1)
                                            
                                            # 方法1: 尝试标准点击
                                            try:
                                                if agreement_element.is_displayed() and agreement_element.is_enabled():
                                                    agreement_element.click()
                                                    logging.info("通过标准方法勾选同意协议")
                                                    agreement_checked = True
                                                    break
                                            except Exception:
                                                logging.warning("标准点击失败，尝试JavaScript点击")
                                            
                                            # 方法2: 尝试JavaScript点击
                                            try:
                                                driver.execute_script("arguments[0].click();", agreement_element)
                                                logging.info("通过JavaScript勾选同意协议")
                                                agreement_checked = True
                                                break
                                            except Exception:
                                                logging.warning("JavaScript点击失败")
                                    except Exception as e:
                                        logging.warning(f"定位或点击同意协议失败 (方式 {i+1}): {e}")
                                
                                # 尝试点击注册按钮 - 按照同意协议的方法重构
                                if agreement_checked:
                                    logging.info("同意协议已勾选，开始尝试点击注册按钮")
                                    
                                    register_button_clicked = False
                                    register_button_locators = [
                                        # 方法0: 基于用户提供的精确HTML元素（最高优先级）
                                        (By.XPATH, "//button[@type='submit' and contains(@class, 'ant-btn-primary') and .//span='注册']"),
                                        (By.CSS_SELECTOR, "button[type='submit'].ant-btn-primary.ant-btn-block span"),
                                        (By.XPATH, "//button[@type='submit' and contains(@class, 'css-zqbva3')]"),
                                        (By.XPATH, "//button[@type='submit' and contains(@class, 'ant-btn-two-chinese-chars')]"),
                                        (By.XPATH, "//button[@type='submit' and contains(@style, 'margin-bottom: 4px')]"),
                                        (By.XPATH, "//span[text()='注册']/parent::button[@type='submit']"),
                                        
                                        # 方法1: 优先使用type="submit"的按钮
                                        (By.XPATH, "//*[@type='submit']"),
                                        # 方法2: 查找具有注册相关文本的按钮
                                        (By.XPATH, "//button[contains(text(), '注册') or contains(text(), 'Register')]"),
                                        # 方法3: 通过class查找按钮
                                        (By.XPATH, "//button[contains(@class, 'register') or contains(@class, 'submit') or contains(@class, 'btn-primary')]"),
                                        # 方法4: 通过name属性查找
                                        (By.XPATH, "//*[@name='register' or @name='submit']"),
                                        # 方法5: 查找form中的最后一个按钮（通常是提交按钮）
                                        (By.XPATH, "//form//button[last()]")
                                    ]
                                    
                                    for i, (by, value) in enumerate(register_button_locators):
                                        try:
                                            logging.info(f"尝试定位注册按钮 (方式 {i+1}/{len(register_button_locators)}): {by}={value}")
                                            
                                            # 首先尝试找到元素
                                            register_buttons = driver.find_elements(by, value)
                                            if register_buttons:
                                                register_button = register_buttons[0]
                                                
                                                # 先滚动到元素可见
                                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", register_button)
                                                time.sleep(1)
                                                
                                                # 检查是否被禁用
                                                is_disabled = register_button.get_attribute('disabled') is not None or \
                                                             (register_button.get_attribute('class') and 'disabled' in register_button.get_attribute('class'))
                                                if is_disabled:
                                                    logging.warning("注册按钮当前被禁用，尝试启用")
                                                    # 尝试通过JavaScript移除disabled属性
                                                    driver.execute_script("arguments[0].removeAttribute('disabled');", register_button)
                                                    driver.execute_script("arguments[0].classList.remove('disabled');", register_button)
                                                    time.sleep(1)
                                                
                                                # 方法1: 尝试标准点击
                                                try:
                                                    if register_button.is_displayed() and register_button.is_enabled():
                                                        register_button.click()
                                                        logging.info("通过标准方法点击注册按钮")
                                                        register_button_clicked = True
                                                        break
                                                except Exception:
                                                    logging.warning("标准点击失败，尝试JavaScript点击")
                                                
                                                # 方法2: 尝试JavaScript点击
                                                try:
                                                    driver.execute_script("arguments[0].click();", register_button)
                                                    logging.info("通过JavaScript点击注册按钮")
                                                    register_button_clicked = True
                                                    break
                                                except Exception:
                                                    logging.warning("JavaScript点击失败")
                                        except Exception as e:
                                            logging.warning(f"定位或点击注册按钮失败 (方式 {i+1}): {e}")
                                    
                                    # 如果所有定位方式都失败，尝试直接提交表单
                                    if not register_button_clicked:
                                        try:
                                            logging.info("所有按钮定位方式失败，尝试直接提交表单")
                                            driver.execute_script("""
                                                var forms = document.querySelectorAll('form');
                                                if (forms.length > 0) {
                                                    forms[0].submit();
                                                    return true;
                                                }
                                                return false;
                                            """)
                                            register_button_clicked = True
                                            logging.info("尝试直接提交表单")
                                        except Exception as e:
                                            logging.warning(f"直接提交表单失败: {e}")
                                            time.sleep(2)
                                    
                                    if register_button_clicked:
                                        logging.info("注册按钮点击成功，等待页面响应")
                                        time.sleep(20)  # 给足够时间让页面重定向
                                        
                                        # 检查是否注册成功（根据URL或页面内容）
                                        success = False
                                        current_url = driver.current_url
                                        if 'success' in current_url.lower() or 'login' in current_url.lower() or 'dashboard' in current_url.lower():
                                            success = True
                                            logging.info(f"注册可能成功，当前URL: {current_url}")
                                        
                                        # 也可以检查页面中的成功提示
                                        try:
                                            success_elements = driver.find_elements(
                                                By.XPATH, "//*[contains(text(), '成功') or contains(text(), 'Success') or contains(text(), '欢迎') or contains(text(), 'welcome')]"
                                            )
                                            if success_elements:
                                                success = True
                                                logging.info("找到成功提示元素，注册可能成功")
                                        except Exception:
                                            pass
                                        
                                        if success:
                                             logging.info("注册成功！停留在重定向页面")
                                             # 确保停留在重定向页面，添加显式的等待和提示
                                             print("\n注册成功！浏览器将保持打开状态，您可以查看重定向页面。")
                                             print(f"当前URL: {current_url}")
                                             print("按Enter键继续或等待30秒后自动关闭...")
                                             
                                             # 让浏览器保持打开一段时间，用户可以查看页面
                                             try:
                                                 import threading
                                                 
                                                 # 设置标志来控制是否保持浏览器打开
                                                 keep_browser_open = True
                                                 
                                                 # 定义一个函数用于等待用户输入
                                                 def wait_for_user():
                                                     global keep_browser_open
                                                     try:
                                                         input()  # 等待用户按Enter
                                                     except:
                                                         pass
                                                     keep_browser_open = False
                                                     print("准备关闭浏览器...")
                                                 
                                                 # 启动线程等待用户输入
                                                 thread = threading.Thread(target=wait_for_user)
                                                 thread.daemon = True
                                                 thread.start()
                                                 
                                                 # 主线程等待30秒或直到用户输入
                                                 import time
                                                 for i in range(30):
                                                     if not keep_browser_open:
                                                         break
                                                     time.sleep(1)
                                                 
                                                 logging.info("浏览器保持打开时间结束")
                                             except Exception as e:
                                                 logging.warning(f"保持浏览器打开过程中出现异常: {e}")
                                             
                                             # 设置一个全局标志，表示注册成功
                                             globals().setdefault('REGISTRATION_SUCCESS', True)
                                else:
                                    logging.error("无法勾选同意协议")
                            else:
                                logging.error("无法定位验证码输入框")
            except Exception as e:
                logging.error(f"触发验证码发送过程出错: {str(e)}")
            
            # 验证码已经在前面的逻辑中获取，这里只需要处理未获取到验证码的情况
            if not 'code' in locals() or code is None:
                code = None
                if len(driver.window_handles) > 0:
                    driver.switch_to.window(driver.window_handles[0])
                    code = get_verification_code(driver)
                    
                    if code:
                        logging.info(f"获取到验证码: {code}")
                        
                        # 切换回注册标签页填写验证码
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[1])
                        
                        # 填写验证码 - 改进版定位策略
                        code_input = None
                        code_locators = [
                            # 新增：更广泛的placeholder匹配
                            (By.XPATH, "//input[contains(@placeholder, '验证码') or contains(@placeholder, 'Verification') or contains(@placeholder, 'code')]"),
                            # 新增：通过类型和属性组合定位
                            (By.XPATH, "//input[@type='text'][contains(@placeholder, 'code')]") ,
                            # 新增：通过表单字段名称属性
                            (By.XPATH, "//input[contains(@name, 'verification') or contains(@name, 'code')]"),
                            # 新增：通过ID属性
                            (By.XPATH, "//input[contains(@id, 'verification') or contains(@id, 'code')]"),
                            # 新增：通过class属性包含验证相关字样
                            (By.XPATH, "//input[contains(@class, 'verification') or contains(@class, 'validate')]") ,
                            # 原有定位器
                            (By.NAME, 'code'),
                            (By.ID, 'code'),
                            (By.CSS_SELECTOR, "input[name='code']"),
                            (By.XPATH, "//input[contains(@class, 'code')]"),
                            # 新增：第3个输入框（通常验证码是第三个输入框）
                            (By.XPATH, "//input[3]"),
                            # 新增：第4个输入框
                            (By.XPATH, "//input[4]")
                        ]
                        for i, (by, value) in enumerate(code_locators):
                            try:
                                logging.info(f"尝试定位验证码输入框 (方式 {i+1}/{len(code_locators)}): {by}={value}")
                                # 先滚动到元素可见
                                code_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((by, value)))
                                if code_input:
                                    # 尝试滚动元素到可见区域
                                    driver.execute_script("arguments[0].scrollIntoView(true);", code_input)
                                    time.sleep(0.5)
                                    logging.info("成功定位验证码输入框")
                                    break
                            except Exception as e:
                                logging.warning(f"定位验证码输入框失败 (方式 {i+1}): {e}")
                        
                        if code_input:
                            code_input.clear()
                            code_input.send_keys(code)
                            logging.info(f"已填写验证码: {code}")
                        else:
                            logging.error("无法定位验证码输入框")
                        
                        # 勾选同意协议 - 增强版定位策略
                        agreement_checked = False
                        agreement_locators = [
                            # 新增：更精确的复选框定位
                            (By.XPATH, "//input[@type='checkbox']"),
                            (By.XPATH, "//input[@type='checkbox']/following-sibling::span"),
                            (By.XPATH, "//input[@type='checkbox']/preceding-sibling::span"),
                            (By.CSS_SELECTOR, "[type='checkbox']"),
                            
                            # 新增：通过标签文本查找
                            (By.XPATH, "//label[contains(., '同意') or contains(., 'agree')]"),
                            (By.XPATH, "//span[contains(., '同意') or contains(., 'agree')]"),
                            (By.XPATH, "//div[contains(., '同意') or contains(., 'agree')]"),
                            
                            # 针对用户提供的HTML结构的特定定位器
                            (By.XPATH, "//span[contains(@class, 'ant-checkbox-label')]"),
                            (By.XPATH, "//span[contains(@class, 'ant-typography') and contains(text(), '我已阅读并同意')]/parent::span"),
                            (By.XPATH, "//span[contains(@class, 'css-zqbva3') and contains(text(), '我已阅读并同意')]/parent::span"),
                            
                            # 原有定位器
                            (By.CSS_SELECTOR, '.agreement-checkbox'),
                            (By.ID, 'agreement'),
                            (By.XPATH, "//div[contains(@class, 'agreement')]"),
                            (By.XPATH, "//span[contains(@class, 'checkbox')]"),
                            (By.XPATH, "//*[contains(text(), '服务条款') or contains(text(), 'Terms')]")
                        ]
                        
                        for i, (by, value) in enumerate(agreement_locators):
                            try:
                                logging.info(f"尝试定位同意协议元素 (方式 {i+1}/{len(agreement_locators)}): {by}={value}")
                                
                                # 首先尝试找到元素（不一定要可点击）
                                agreement_elements = driver.find_elements(by, value)
                                if agreement_elements:
                                    agreement_element = agreement_elements[0]  # 使用第一个找到的元素
                                    
                                    # 先滚动到元素可见
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", agreement_element)
                                    time.sleep(1)
                                    
                                    # 方法1: 尝试标准点击
                                    try:
                                        if agreement_element.is_displayed() and agreement_element.is_enabled():
                                            agreement_element.click()
                                            logging.info("通过标准方法勾选同意协议")
                                            agreement_checked = True
                                            break
                                    except Exception:
                                        logging.warning(f"标准点击失败，尝试JavaScript点击")
                                    
                                    # 方法2: 尝试JavaScript点击
                                    try:
                                        # 点击元素
                                        driver.execute_script("arguments[0].click();", agreement_element)
                                        logging.info("通过JavaScript勾选同意协议")
                                        agreement_checked = True
                                        break
                                    except Exception:
                                        logging.warning(f"JavaScript点击失败，尝试点击其父元素")
                                    
                                    # 方法3: 尝试点击其父元素
                                    try:
                                        parent_element = driver.execute_script("return arguments[0].parentNode;", agreement_element)
                                        if parent_element:
                                            driver.execute_script("arguments[0].click();", parent_element)
                                            logging.info("通过JavaScript点击父元素勾选同意协议")
                                            agreement_checked = True
                                            break
                                    except Exception:
                                        logging.warning(f"点击父元素失败")
                            except Exception as e:
                                logging.warning(f"定位或勾选同意协议失败 (方式 {i+1}): {e}")
                        
                        # 最终方案: 如果以上都失败，尝试直接通过JavaScript设置checkbox选中
                        if not agreement_checked:
                            try:
                                logging.info("尝试直接通过JavaScript选中所有checkbox")
                                driver.execute_script("""
                                    var checkboxes = document.querySelectorAll('input[type="checkbox"]');
                                    checkboxes.forEach(function(checkbox) {
                                        if (!checkbox.checked) {
                                            checkbox.checked = true;
                                            // 触发change事件
                                            var event = new Event('change', { bubbles: true });
                                            checkbox.dispatchEvent(event);
                                        }
                                    });
                                """)
                                agreement_checked = True
                                logging.info("已通过JavaScript强制选中所有checkbox")
                            except Exception as e:
                                logging.error(f"JavaScript强制选中checkbox失败: {e}")
                        
                        if not agreement_checked:
                            logging.warning("无法勾选同意协议")
                        
                        # 先尝试自动点击注册按钮，失败后再提示用户手动点击
                        register_button_clicked = False
                        
                        try:
                            logging.info("尝试自动点击注册按钮...")
                            
                            # 方法1: 优先使用type="submit"属性定位（用户建议）
                            register_buttons = driver.find_elements(
                                By.XPATH, "//button[@type='submit']")
                            
                            # 方法2: 如果方法1失败，使用包含"注册"文本的按钮
                            if not register_buttons:
                                register_buttons = driver.find_elements(
                                    By.XPATH, "//button[contains(text(), '注册')]")
                            
                            # 方法3: 如果前两种方法都失败，使用用户提供的HTML结构定位
                            if not register_buttons:
                                register_buttons = driver.find_elements(
                                    By.XPATH, "//button[contains(@class, 'ant-btn-primary') and contains(@class, 'ant-btn-block')]")
                            
                            # 方法4: 最后使用完整XPATH
                            if not register_buttons:
                                register_buttons = driver.find_elements(
                                    By.XPATH, "//*[@id='root']/div/section[2]/section/div[2]/div/form/button")
                            
                            if register_buttons:
                                register_button = register_buttons[0]
                                # 滚动到按钮可见
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", register_button)
                                time.sleep(1)
                                
                                # 检查是否被禁用
                                is_disabled = register_button.get_attribute('disabled') is not None or 'disabled' in register_button.get_attribute('class')
                                if is_disabled:
                                    logging.warning("注册按钮当前被禁用，尝试启用")
                                    # 尝试通过JavaScript移除disabled属性
                                    driver.execute_script("arguments[0].removeAttribute('disabled');", register_button)
                                    driver.execute_script("arguments[0].classList.remove('disabled');", register_button)
                                    time.sleep(1)
                                
                                # 尝试一种全新的方法：直接定位注册表单并提交
                                try:
                                    logging.info("尝试全新的表单提交方法...")
                                    
                                    # 方法1: 直接通过JavaScript提交注册表单（最直接的方法）
                                    driver.execute_script("""
                                        // 1. 查找可能的注册表单
                                        var registerForm = null;
                                        
                                        // 查找包含注册按钮的表单
                                        var registerButton = document.querySelector('button[type="submit"]:not([disabled]), button:contains("注册"):not([disabled])');
                                        if (registerButton) {
                                            registerForm = registerButton.closest('form');
                                        }
                                        
                                        // 如果没找到，尝试其他常见的表单标识
                                        if (!registerForm) {
                                            var forms = document.querySelectorAll('form');
                                            for (var i = 0; i < forms.length; i++) {
                                                var form = forms[i];
                                                // 检查表单是否包含邮箱、手机号、密码等注册字段
                                                if (form.querySelector('input[type="email"]') || 
                                                    form.querySelector('input[placeholder*="邮箱"]') || 
                                                    form.querySelector('input[type="tel"]') || 
                                                    form.querySelector('input[placeholder*="手机"]') || 
                                                    form.querySelector('input[type="password"]')) {
                                                    registerForm = form;
                                                    break;
                                                }
                                            }
                                        }
                                        
                                        // 2. 确保所有字段都已验证
                                        if (registerForm) {
                                            console.log('找到注册表单，准备提交');
                                            
                                            // 保存表单数据
                                            var formData = {};
                                            var inputs = registerForm.querySelectorAll('input, select, textarea');
                                            inputs.forEach(function(input) {
                                                if (input.name || input.id) {
                                                    if (input.type === 'checkbox' || input.type === 'radio') {
                                                        formData[input.name || input.id] = input.checked;
                                                    } else {
                                                        formData[input.name || input.id] = input.value;
                                                    }
                                                }
                                            });
                                            
                                            // 3. 对每个输入字段，确保它们触发了所有必要的事件
                                            inputs.forEach(function(input) {
                                                if (input.type !== 'hidden' && input.disabled !== true) {
                                                    // 触发所有可能的用户交互事件
                                                    var events = ['focus', 'input', 'change', 'blur'];
                                                    events.forEach(function(eventName) {
                                                        input.dispatchEvent(new Event(eventName, { bubbles: true, cancelable: true }));
                                                    });
                                                }
                                            });
                                            
                                            // 4. 短暂延迟确保验证完成
                                            setTimeout(function() {
                                                // 5. 如果有显式的提交按钮，点击它（模拟真实用户行为）
                                                if (registerButton) {
                                                    // 模拟鼠标移动和点击的完整序列
                                                    registerButton.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
                                                    setTimeout(function() {
                                                        registerButton.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                                                        setTimeout(function() {
                                                            registerButton.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                                                            setTimeout(function() {
                                                                registerButton.click();
                                                            }, 30);
                                                        }, 30);
                                                    }, 30);
                                                } else {
                                                    // 6. 如果没有明确的提交按钮，直接提交表单
                                                    console.log('没有找到提交按钮，直接提交表单');
                                                    registerForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                                                }
                                            }, 200);
                                        }
                                    """)
                                    
                                    register_button_clicked = True
                                    logging.info("成功应用全新的表单提交方法")
                                    
                                    # 给表单提交一些时间
                                    time.sleep(3)
                                except Exception as e_new:
                                    logging.warning(f"全新表单提交方法失败: {e_new}")
                                    
                                    # 尝试原始方法
                                    try:
                                        logging.info("回退到原始点击方法")
                                        register_button.click()
                                        register_button_clicked = True
                                        logging.info("成功通过普通方式点击注册按钮")
                                    except Exception as e_click:
                                        logging.warning(f"普通点击注册按钮失败: {e_click}")
                                    
                                    # 方法1: 普通点击
                                    try:
                                        register_button.click()
                                        register_button_clicked = True
                                        logging.info("成功通过普通方式点击注册按钮")
                                    except Exception as e1:
                                        logging.warning(f"普通点击注册按钮失败: {e1}")
                                        
                                        # 方法2: JavaScript点击
                                        try:
                                            driver.execute_script("arguments[0].click();", register_button)
                                            register_button_clicked = True
                                            logging.info("成功通过JavaScript点击注册按钮")
                                        except Exception as e2:
                                            logging.warning(f"JavaScript点击注册按钮失败: {e2}")
                                            
                                            # 方法3: ActionChains点击
                                            try:
                                                actions = ActionChains(driver)
                                                actions.move_to_element(register_button).click().perform()
                                                register_button_clicked = True
                                                logging.info("成功通过ActionChains点击注册按钮")
                                            except Exception as e3:
                                                logging.error(f"ActionChains点击注册按钮失败: {e3}")
                            else:
                                logging.warning("未找到注册按钮")
                                
                        except Exception as e:
                            logging.error(f"自动点击注册按钮过程中发生错误: {e}")
                        
                        # 如果自动点击失败，提示用户手动点击
                        if not register_button_clicked:
                            logging.info("===============================")
                            logging.info("自动点击注册按钮失败，请您手动点击注册按钮完成注册操作")
                            logging.info("注册按钮位置: //*[@id='root']/div/section[2]/section/div[2]/div/form/button")
                            logging.info("按钮信息: <button type=\"submit\" class=\"ant-btn css-zqbva3 ant-btn-primary ant-btn-color-primary ant-btn-variant-solid ant-btn-lg ant-btn-two-chinese-chars ant-btn-block\">")
                            logging.info("请在浏览器中找到并点击注册按钮")
                            logging.info("===============================")
                            
                            # 给用户足够的时间手动点击
                            user_input = input("请在浏览器中点击注册按钮，然后按Enter键继续...")
                            logging.info("用户确认已点击注册按钮，继续进行后续操作")
                        
                        # 等待页面响应
                        time.sleep(5)
                    else:
                        logging.error("注册标签页不存在")
                else:
                    logging.error("无法获取验证码")
            # 移除临时邮箱标签页不存在的检查，因为验证码可能已经通过其他方式获取
                
            # 如果没有获取到验证码，记录错误信息
            if not code:
                logging.error("无法获取验证码")
                result = {
                    'email': email,
                    'nickname': nickname,
                    'password': password,
                    'code': None,
                    'success': False,
                    'error': '无法获取验证码'
                }
                save_result(result)
                # 提前结束，不再继续执行
                return
                
            # 等待注册结果
            time.sleep(5)
            
            # 检查是否注册成功
            success = False
            error_message = "-"
            api_key = "-"
            
            try:
                # 查找成功提示元素（优先使用这个作为成功判断依据）
                success_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '成功') or contains(text(), 'Success') or contains(text(), 'welcome') or contains(text(), '欢迎')]")
                if success_elements:
                    success = True
                    logging.info(f"找到成功提示元素，注册可能成功")
                    logging.info(f"注册成功！停留在重定向页面")
                
                # 检查URL变化作为辅助判断
                if not success:
                    current_url = driver.current_url
                    if 'success' in current_url.lower() or 'login' in current_url.lower() or 'dashboard' in current_url.lower() or 'home' in current_url.lower():
                        success = True
                        logging.info(f"URL表示成功: {current_url}")
                
                # 注册成功后获取API Key
                if success:
                    try:
                        # 设置全局标志，表示注册成功
                        global REGISTRATION_SUCCESS
                        REGISTRATION_SUCCESS = True
                        
                        # 新打开一个标签页
                        driver.execute_script("window.open('');")
                        # 切换到新标签页
                        driver.switch_to.window(driver.window_handles[1])
                        
                        # 访问个人中心页面
                        api_url = "https://www.daydaymap.com/personalCenter?userMenu=personal"
                        logging.info(f"正在访问API Key页面: {api_url}")
                        driver.get(api_url)
                        
                        # 等待页面加载
                        time.sleep(3)
                        
                        # 查找API Key区域
                        try:
                            api_key_element = driver.find_element(By.XPATH, "//*[@id='root']/div/div/div[2]/div/main/div/div[2]/div/div/div[2]/div[6]")
                            logging.info("找到API Key区域")
                            
                            # 尝试点击复制按钮 - 使用专门的SVG复制按钮处理函数
                            try:
                                # 调用专门的copy_api_key函数，优先处理SVG复制按钮
                                copy_success = copy_api_key(driver)
                                if copy_success:
                                    logging.info("使用专门的复制函数成功复制API Key")
                                else:
                                    logging.warning("专门的复制函数失败，将尝试使用原有方式和文本提取作为备选")
                                    
                                    # 原有复制按钮查找逻辑作为备选
                                    try:
                                        # 尝试找到复制按钮
                                        copy_button = None
                                        
                                        # 增强的定位策略 - 尝试多种方式
                                        copy_locators = [
                                            # 查找区域内的所有按钮并检查文本
                                            lambda: next((b for b in api_key_element.find_elements(By.TAG_NAME, 'button') 
                                                         if '复制' in b.text or 'copy' in b.text.lower()), None),
                                            # 查找span元素
                                            lambda: api_key_element.find_element(By.XPATH, ".//span[contains(@class, 'copy') or contains(text(), '复制')]"),
                                            # 查找任何包含复制文本的元素
                                            lambda: api_key_element.find_element(By.XPATH, ".//*[contains(text(), '复制') or contains(text(), 'Copy')]"),
                                            # 查找icon元素
                                            lambda: api_key_element.find_element(By.XPATH, ".//i[contains(@class, 'copy')]"),
                                            # 查找button或a标签
                                            lambda: api_key_element.find_element(By.XPATH, ".//button | .//a"),
                                            # 查找具有点击事件的元素
                                            lambda: api_key_element.find_element(By.XPATH, ".//*[@onclick or @data-click]"),
                                        ]
                                        
                                        # 尝试每种定位策略
                                        for i, locator_func in enumerate(copy_locators):
                                            try:
                                                found_button = locator_func()
                                                if found_button and found_button.is_displayed():
                                                    copy_button = found_button
                                                    logging.info(f"使用策略 {i+1} 找到复制按钮")
                                                    break
                                            except:
                                                continue
                                        
                                        if copy_button:
                                            # 使用JavaScript点击
                                            try:
                                                driver.execute_script("arguments[0].click();", copy_button)
                                                logging.info("已点击复制按钮")
                                            except Exception as click_error:
                                                logging.warning(f"点击复制按钮失败: {click_error}")
                                        else:
                                            logging.warning("无法找到复制按钮，将直接尝试提取API Key文本")
                                    except Exception as copy_error:
                                        logging.warning(f"复制按钮定位过程出错: {copy_error}")
                            except Exception as copy_function_error:
                                logging.warning(f"调用复制函数过程出错: {copy_function_error}")
                                # 继续执行后面的文本提取逻辑作为最后的备选方案
                            
                            # 无论复制按钮是否找到，都尝试提取API Key文本
                            try:
                                # 尝试多种方式提取API Key文本
                                api_key_text = ""
                                logging.info("开始提取API Key文本...")
                                
                                # 1. 打印整个元素的完整文本，用于调试
                                full_text = api_key_element.text
                                logging.info(f"API Key元素完整文本: {full_text}")
                                
                                # 2. 直接获取元素文本
                                if full_text:
                                    # 尝试多种模式匹配API Key
                                    patterns = [
                                        r'[A-Za-z0-9]{32,}',  # 至少32位的字母数字
                                        r'[A-Za-z0-9_-]{20,}',  # 包含下划线和连字符
                                        r'[0-9a-fA-F]{32}',     # 32位十六进制
                                        r'API[\s_-]?Key[\s:]+([A-Za-z0-9_-]+)',  # API Key: xxx格式
                                    ]
                                    
                                    for pattern in patterns:
                                        matches = re.findall(pattern, full_text)
                                        if matches:
                                            api_key_text = matches[0]
                                            logging.info(f"使用模式 {pattern} 找到API Key")
                                            break
                                
                                # 3. 如果直接提取失败，尝试查找input或其他包含key的元素
                                if not api_key_text:
                                    key_inputs = api_key_element.find_elements(By.TAG_NAME, 'input')
                                    for i, inp in enumerate(key_inputs):
                                        value = inp.get_attribute('value')
                                        if value and len(value) > 20:
                                            api_key_text = value
                                            logging.info(f"从输入框 {i+1} 获取到API Key")
                                            break
                                
                                # 4. 尝试查找具有data-*属性的元素
                                if not api_key_text:
                                    data_elements = api_key_element.find_elements(By.XPATH, ".//*[@data-key or @data-api-key or @data-value]")
                                    for elem in data_elements:
                                        data_key = elem.get_attribute('data-key') or elem.get_attribute('data-api-key') or elem.get_attribute('data-value')
                                        if data_key and len(data_key) > 20:
                                            api_key_text = data_key
                                            logging.info("从data属性获取到API Key")
                                            break
                                
                                # 5. 最后尝试获取所有子元素的文本
                                if not api_key_text:
                                    all_elements = api_key_element.find_elements(By.XPATH, './/*')
                                    logging.info(f"在API Key区域找到 {len(all_elements)} 个子元素")
                                    
                                    # 检查每个子元素的文本和属性
                                    for i, elem in enumerate(all_elements[:20]):  # 限制检查的元素数量
                                        try:
                                            elem_text = elem.text
                                            elem_id = elem.get_attribute('id') or '无ID'
                                            elem_class = elem.get_attribute('class') or '无class'
                                            
                                            if elem_text:
                                                logging.info(f"子元素 {i}: ID={elem_id}, class={elem_class}, 文本={elem_text}")
                                                # 对每个子元素应用模式匹配
                                                for pattern in patterns:
                                                    matches = re.findall(pattern, elem_text)
                                                    if matches:
                                                        api_key_text = matches[0]
                                                        logging.info(f"从子元素 {i} 找到API Key")
                                                        break
                                                if api_key_text:
                                                    break
                                        except:
                                            continue
                                    
                                    # 如果仍然找不到，尝试组合所有文本
                                    if not api_key_text:
                                        all_texts = ' '.join([elem.text for elem in all_elements if elem.text])
                                        for pattern in patterns:
                                            matches = re.findall(pattern, all_texts)
                                            if matches:
                                                api_key_text = matches[0]
                                                break
                                
                                if api_key_text:
                                    api_key = api_key_text
                                    logging.info(f"成功获取API Key: {api_key[:10]}...")
                                else:
                                    logging.warning("无法提取API Key文本，请检查页面结构")
                                    
                                    # 保存页面源码用于调试
                                    try:
                                        page_source = driver.page_source
                                        with open('api_key_page_debug.html', 'w', encoding='utf-8') as f:
                                            f.write(page_source)
                                        logging.info("已保存页面源码到 api_key_page_debug.html 用于调试")
                                    except:
                                        pass
                            except Exception as key_extract_error:
                                logging.warning(f"提取API Key时出错: {key_extract_error}")
                        except Exception as api_element_error:
                            logging.warning(f"查找API Key区域时出错: {api_element_error}")
                            
                        # 关闭API Key标签页，返回主标签页
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except Exception as api_error:
                        logging.warning(f"获取API Key过程出错: {api_error}")
            except Exception as e:
                logging.error(f"检查注册结果时出错: {e}")
            
            result = {
                'email': email,
                'nickname': nickname,
                'password': password,
                'code': code,
                'success': success,
                'error': error_message,
                'api_key': api_key
            }
            
            # 保存结果到文件
            save_result(result)
                
            if success:
                logging.info("注册成功！")
            else:
                logging.warning("注册失败，请检查可能的错误")
        except Exception as e:
            logging.error(f"填写表单时出错: {e}")
            result = {
                'email': email,
                'nickname': nickname,
                'password': password,
                'code': None,
                'success': False,
                'error': str(e)
            }
            save_result(result)
    except Exception as e:
        logging.error(f"注册过程出错: {e}")
        # 保存错误信息
        result = {
            'email': '未知',
            'nickname': '未知',
            'password': '未知',
            'code': None,
            'success': False,
            'error': f'注册过程出错: {str(e)}'
        }
        save_result(result)
    finally:
        # 检查是否注册成功，如果成功则不关闭浏览器
        registration_success = globals().get('REGISTRATION_SUCCESS', False)
        if not registration_success and driver:
            try:
                driver.quit()
                logging.info("浏览器已关闭")
            except:
                pass
        elif registration_success:
            logging.info("注册成功！浏览器保持打开状态，用户可以查看重定向页面。")
            print("\n注意：浏览器保持打开状态。您可以手动关闭浏览器。")

# 保存结果到文件
def save_result(result):
    try:
        # 确保文件路径正确
        import os
        file_path = os.path.join(os.getcwd(), 'results.md')
        
        # 清理和安全化数据
        def sanitize_value(value):
            if value is None:
                return "None"
            # 转换为字符串并处理可能的编码问题
            value_str = str(value)
            # 替换表格分隔符和换行符
            value_str = value_str.replace("|", "-")
            value_str = value_str.replace("\n", " ")
            # 限制长度
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            return value_str
        
        # 准备安全的结果数据
        safe_result = {
            'email': sanitize_value(result.get('email', '未知')),
            'nickname': sanitize_value(result.get('nickname', '未知')),
            'password': sanitize_value(result.get('password', '未知')),
            'code': sanitize_value(result.get('code', '-')),
            'success': result.get('success', False),
            'error': sanitize_value(result.get('error', '-')),
            'api_key': sanitize_value(result.get('api_key', '-'))
        }
        
        # 读取现有结果
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        except FileNotFoundError:
            # 使用更简单的表头，避免特殊字符
            existing_content = "# 注册结果\n\n"
            existing_content += "| 邮箱 | 昵称 | 密码 | 验证码 | 注册状态 | 错误信息 | API Key |\n"
            existing_content += "|------|------|------|--------|----------|----------|---------|\n"
        except UnicodeDecodeError:
            # 如果编码错误，重新创建文件
            logging.warning("文件编码错误，重新创建结果文件")
            existing_content = "# 注册结果\n\n"
            existing_content += "| 邮箱 | 昵称 | 密码 | 验证码 | 注册状态 | 错误信息 | API Key |\n"
            existing_content += "|------|------|------|--------|----------|----------|---------|\n"
        
        # 添加新结果，使用简单的状态表示
        status = "成功" if safe_result['success'] else "失败"
        
        # 构建新行，确保所有字段都被正确处理
        new_line = f"| {safe_result['email']} | {safe_result['nickname']} | {safe_result['password']} | {safe_result['code']} | {status} | {safe_result['error']} | {safe_result['api_key']} |\n"
        
        # 写入文件 - 尝试多种编码
        encoding_success = False
        encodings_to_try = ['utf-8', 'utf-8-sig', 'gbk', 'cp936']
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(existing_content + new_line)
                logging.info(f"结果已使用{encoding}编码保存到 {file_path}")
                encoding_success = True
                break
            except Exception as enc_e:
                logging.warning(f"使用{encoding}编码保存失败: {enc_e}")
        
        # 如果所有编码都失败，使用二进制模式保存
        if not encoding_success:
            try:
                # 将字符串转换为字节，替换无法编码的字符
                content_bytes = (existing_content + new_line).encode('utf-8', errors='replace')
                with open(file_path, 'wb') as f:
                    f.write(content_bytes)
                logging.info(f"使用二进制模式成功保存结果到 {file_path}")
            except Exception as binary_e:
                logging.error(f"所有保存方式都失败: {binary_e}")
                # 最后尝试打印到控制台
                print("\n===== 无法保存到文件，结果如下 =====")
                print(f"邮箱: {safe_result['email']}")
                print(f"昵称: {safe_result['nickname']}")
                print(f"密码: {safe_result['password']}")
                print(f"验证码: {safe_result['code']}")
                print(f"注册状态: {status}")
                print(f"错误信息: {safe_result['error']}")
                print(f"API Key: {safe_result['api_key']}")
                print(f"API Key: {safe_result['api_key']}")
                print("=================================\n")
    
    except Exception as e:
        logging.error(f"保存结果时出错: {e}")
        # 紧急打印结果到控制台
        try:
            print("\n紧急结果输出:")
            for key, value in result.items():
                print(f"{key}: {value}")
        except:
            pass

# 执行注册
if __name__ == "__main__":
    logging.info("开始注册过程...")
    register_account()
    logging.info("注册过程完成。")
    
    # 显示结果文件路径
    try:
        import os
        result_file_path = os.path.abspath('results.md')
        logging.info(f"注册结果保存在: {result_file_path}")
    except:
        pass

# 通用元素等待函数
def wait_for_element(driver, by, value, timeout=10, description="元素"):
    """通用元素等待函数，带详细日志和重试逻辑"""
    logging.info(f"等待{description}: {by}={value}")
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        # 确保元素可见
        WebDriverWait(driver, timeout).until(
            EC.visibility_of(element)
        )
        # 滚动到元素可见
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.5)
        logging.info(f"成功找到{description}")
        return element
    except Exception as e:
        logging.error(f"等待{description}失败: {e}")
        return None

# 安全点击函数
def safe_click(driver, element, description="元素"):
    """安全点击函数，尝试多种点击方式"""
    if not element:
        logging.error(f"无法点击{description}: 元素不存在")
        return False
    
    # 先滚动到元素
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.5)
    except Exception as e:
        logging.warning(f"滚动到{description}时出错: {e}")
    
    # 尝试普通点击
    try:
        element.click()
        logging.info(f"成功点击{description} (普通点击)")
        return True
    except Exception as e1:
        logging.warning(f"普通点击{description}失败: {e1}")
        
    # 尝试JavaScript点击
    try:
        driver.execute_script("arguments[0].click();", element)
        logging.info(f"成功点击{description} (JavaScript点击)")
        return True
    except Exception as e2:
        logging.warning(f"JavaScript点击{description}失败: {e2}")
        
    # 尝试ActionChains点击
    try:
        actions = ActionChains(driver)
        actions.move_to_element(element).click().perform()
        logging.info(f"成功点击{description} (ActionChains点击)")
        return True
    except Exception as e3:
        logging.error(f"ActionChains点击{description}失败: {e3}")
    
    return False

# 智能验证码发送函数
def trigger_verification_code(driver):
    """
    智能触发验证码发送，尝试多种策略确保验证码能够发送
    
    Args:
        driver: WebDriver实例
    
    Returns:
        bool: 是否成功触发验证码发送
    """
    logging.info("开始尝试触发验证码发送...")
    
    # 验证码输入框定位策略
    verification_input_locators = [
        (By.XPATH, "//input[@placeholder='Please enter the verification code']"),
        (By.XPATH, "//input[contains(@placeholder, 'verification')]"),
        (By.XPATH, "//input[contains(@placeholder, '验证码')]"),
        (By.XPATH, "//input[@type='text' and contains(@class, 'verification')]"),
        (By.XPATH, "//input[@id='verification-code']"),
        (By.XPATH, "//input[contains(@id, 'code')]")
    ]
    
    verification_input = None
    
    # 尝试定位验证码输入框
    for locator_type, locator_value in verification_input_locators:
        try:
            verification_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((locator_type, locator_value)))
            logging.info(f"成功定位到验证码输入框: {locator_type}={locator_value}")
            
            # 滚动到验证码输入框可见
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", verification_input)
            time.sleep(0.5)
            break
        except Exception as e:
            logging.warning(f"使用定位器 {locator_type}={locator_value} 未找到验证码输入框: {e}")
    
    if not verification_input:
        logging.error("无法定位验证码输入框")
        return False
    
    # 保存当前窗口句柄，以便后续可能的操作
    current_window = driver.current_window_handle
    
    # 综合触发策略
    strategies = []
    
    # 策略1: 查找父元素内的可点击元素
    try:
        parent_element = verification_input.find_element(By.XPATH, '..')
        nearby_elements = parent_element.find_elements(By.XPATH, './/*')
        logging.info(f"在验证码输入框父元素中找到 {len(nearby_elements)} 个元素")
        
        # 诊断并添加可能的触发元素
        for i, elem in enumerate(nearby_elements[:15]):  # 限制数量避免过多尝试
            try:
                if elem.is_displayed() and elem.is_enabled() and elem != verification_input:
                    elem_text = elem.text.strip()
                    elem_tag = elem.tag_name
                    elem_class = elem.get_attribute('class')
                    elem_id = elem.get_attribute('id')
                    
                    # 判断是否可能是发送按钮
                    if (elem_tag in ['button', 'a', 'input'] or 
                        'code' in (elem_class or '').lower() or 
                        'send' in (elem_class or '').lower() or
                        '获取' in elem_text or 'send' in elem_text.lower() or 'code' in elem_text.lower()):
                        strategies.append((elem, f"父元素内元素 {i+1}: 标签={elem_tag}, 文本='{elem_text}'"))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"获取父元素信息失败: {e}")
    
    # 策略2: 查找所有包含code/send相关文本或类名的元素
    try:
        code_elements = driver.find_elements(By.XPATH, 
            "//*[(contains(text(), 'code') or contains(text(), 'Code') or contains(text(), '验证码') or "
            "contains(text(), '获取') or contains(text(), 'send') or contains(text(), 'Send') or "
            "contains(@class, 'code') or contains(@id, 'code') or contains(@class, 'send') or "
            "contains(@id, 'send')) and not contains(@placeholder, 'verification')]"
        )
        
        for elem in code_elements[:10]:  # 限制数量
            try:
                if elem.is_displayed() and elem.is_enabled() and elem != verification_input:
                    elem_text = elem.text.strip()
                    elem_tag = elem.tag_name
                    strategies.append((elem, f"全局code元素: 标签={elem_tag}, 文本='{elem_text}'"))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"查找全局code元素失败: {e}")
    
    # 策略3: 尝试JavaScript查找和点击
    strategies.append((None, "JavaScript查找策略"))
    
    # 策略4: 点击验证码输入框后重新输入邮箱（模拟用户操作）
    strategies.append((None, "重新输入邮箱策略"))
    
    # 执行所有策略
    success = False
    for elem, strategy_name in strategies:
        try:
            logging.info(f"尝试策略: {strategy_name}")
            
            if elem:
                # 对找到的元素执行点击
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                time.sleep(0.5)
                
                # 尝试多种点击方式
                try:
                    elem.click()
                    logging.info(f"成功点击元素: {strategy_name}")
                except:
                    try:
                        driver.execute_script("arguments[0].click();", elem)
                        logging.info(f"通过JavaScript成功点击元素: {strategy_name}")
                    except:
                        try:
                            actions = ActionChains(driver)
                            actions.move_to_element(elem).click().perform()
                            logging.info(f"通过ActionChains成功点击元素: {strategy_name}")
                        except:
                            logging.warning(f"所有点击方式都失败: {strategy_name}")
                            continue
                
                time.sleep(1.5)  # 等待可能的反馈
                
                # 检查是否有成功提示
                try:
                    success_messages = driver.find_elements(By.XPATH, 
                        "//*[contains(text(), '已发送') or contains(text(), 'sent') or contains(text(), 'success') or contains(text(), '成功')]"
                    )
                    if success_messages:
                        for msg in success_messages:
                            if msg.is_displayed():
                                logging.info(f"检测到验证码发送成功提示: {msg.text}")
                                success = True
                                break
                except:
                    pass
                
                if success:
                    break
                
            elif strategy_name == "JavaScript查找策略":
                # JavaScript查找和触发策略
                logging.info("执行JavaScript查找验证码发送按钮")
                
                # 执行复杂的JavaScript查找逻辑
                send_button = driver.execute_script("""
                    // 查找可能的发送按钮
                    function findSendButton() {
                        // 针对用户提供的HTML结构的特定查找 - 查找ant-input-suffix中的获取验证码按钮
                        const suffixElements = document.querySelectorAll('.ant-input-suffix');
                        for (const suffix of suffixElements) {
                            const codeLinks = suffix.querySelectorAll('a.ant-typography, a.css-zqbva3');
                            for (const link of codeLinks) {
                                if (link.textContent && link.textContent.includes('获取验证码') && 
                                    link.offsetParent !== null) {
                                    return link;
                                }
                            }
                        }
                        
                        // 针对用户提供的HTML结构的特定查找 - 直接查找带有ant-typography的获取验证码元素
                        const typographyElements = document.querySelectorAll('.ant-typography');
                        for (const element of typographyElements) {
                            if (element.textContent && element.textContent.includes('获取验证码') && 
                                element.offsetParent !== null) {
                                return element;
                            }
                        }
                        
                        // 查找包含特定文本的元素
                        const texts = ['发送验证码', 'Send Code', '获取验证码', 'Get Code', 'send', '获取'];
                        for (const text of texts) {
                            const elements = document.querySelectorAll('*');
                            for (const element of elements) {
                                if (element.textContent && element.textContent.includes(text) && 
                                    element.nodeName.match(/^(BUTTON|A|INPUT|SPAN|DIV)$/) &&
                                    element.offsetParent !== null) {
                                    return element;
                                }
                            }
                        }
                        
                        // 查找特定类名的元素
                        const classes = ['send-code', 'get-code', 'code-btn', 'verify-btn', 'css-zqbva3'];
                        for (const cls of classes) {
                            const element = document.querySelector(`.${cls}`);
                            if (element && element.offsetParent !== null) {
                                return element;
                            }
                        }
                        
                        // 查找验证码输入框旁边的元素（增强版，检查父元素和更多兄弟元素）
                        const inputs = document.querySelectorAll('input');
                        for (const input of inputs) {
                            if (input.placeholder && (input.placeholder.includes('verification') || 
                                                       input.placeholder.includes('验证码'))) {
                                // 检查下一个兄弟元素
                                const sibling = input.nextElementSibling;
                                if (sibling && sibling.nodeName.match(/^(BUTTON|A|INPUT|SPAN|DIV)$/)) {
                                    return sibling;
                                }
                                
                                // 检查父元素
                                const parent = input.parentElement;
                                if (parent) {
                                    // 查找父元素内的所有可能的按钮
                                    const buttons = parent.querySelectorAll('button, a, span, div');
                                    for (const button of buttons) {
                                        if (button !== input && button.offsetParent !== null) {
                                            // 检查是否包含验证码相关文本
                                            if (button.textContent && (button.textContent.includes('获取') || 
                                                                       button.textContent.includes('send') || 
                                                                       button.textContent.includes('code'))) {
                                                return button;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        return null;
                    }
                    
                    const button = findSendButton();
                    if (button) {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        setTimeout(() => button.click(), 500);
                        return true;
                    }
                    return false;
                """)
                
                if send_button:
                    logging.info("JavaScript成功找到并点击发送按钮")
                    time.sleep(2)
                    success = True
                    break
                
            elif strategy_name == "重新输入邮箱策略":
                # 重新输入邮箱策略
                logging.info("执行重新输入邮箱策略")
                
                # 查找邮箱输入框
                try:
                    email_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                        (By.XPATH, "//input[contains(@placeholder, 'email') or contains(@placeholder, 'mail') or contains(@type, 'email')]")
                    ))
                    
                    # 重新输入邮箱
                    current_email = email_input.get_attribute('value')
                    if current_email:
                        email_input.clear()
                        time.sleep(0.5)
                        email_input.send_keys(current_email)
                        logging.info("已重新输入邮箱，可能触发验证码发送")
                        time.sleep(1)
                        
                        # 点击页面其他地方可能触发验证
                        driver.execute_script("document.body.click();")
                        time.sleep(1)
                except Exception as e:
                    logging.warning(f"重新输入邮箱策略失败: {e}")
        
        except Exception as e:
            logging.warning(f"执行策略时出错 {strategy_name}: {e}")
            
        # 检查是否需要处理滑动验证
        try:
            handle_slider_verification(driver)
        except Exception:
            pass
    
    # 如果所有策略都失败，最后尝试直接点击验证码输入框
    if not success:
        try:
            logging.info("尝试最后策略：点击验证码输入框")
            verification_input.click()
            time.sleep(1)
            verification_input.click()  # 再次点击
            time.sleep(1)
            logging.info("已点击验证码输入框")
        except Exception as e:
            logging.warning(f"点击验证码输入框失败: {e}")
    
    logging.info(f"验证码触发流程完成，{'成功' if success else '可能已尝试所有策略'}")
    return success