/**
 * Редактор кода для PyWay с системой автоматического тестирования
 * Аналогичен редактору в Яндекс.Учебнике
 */

// Глобальные переменные редактора
let codeEditor;
let testCases = [];
let isLessonCompleted = false;

// Используем window.lessonConfig или значения по умолчанию
const lessonConfig = window.lessonConfig || {
    lessonId: 0,
    defaultCode: '# Напишите ваш код здесь\n# Используйте print() для вывода результата',
    testCases: [],
    isCompleted: false,
    apiUrl: '/api/execute'
};

console.log('editor.js: Конфигурация загружена', lessonConfig);

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('editor.js: DOMContentLoaded');
    
    // Небольшая задержка для гарантии загрузки всех элементов
    setTimeout(function() {
        initEditor();
        initTestCases();
        setupEventListeners();
        
        // Если урок уже пройден, показываем сообщение
        if (lessonConfig.isCompleted) {
            showCompletionMessage();
        }
        
        console.log('editor.js: Инициализация завершена');
    }, 100);
});

// Инициализация CodeMirror редактора
function initEditor() {
    console.log('initEditor: начало инициализации');
    
    // Проверяем, существует ли элемент
    const editorElement = document.getElementById('code-editor');
    if (!editorElement) {
        console.error('initEditor: Элемент #code-editor не найден!');
        return;
    }
    
    console.log('initEditor: элемент найден, создаём CodeMirror');
    
    try {
        // Создаём редактор CodeMirror
        codeEditor = CodeMirror(editorElement, {
            mode: 'python',
            theme: 'dracula',
            lineNumbers: true,
            indentUnit: 4,
            tabSize: 4,
            indentWithTabs: false,
            lineWrapping: true,
            autoCloseBrackets: true,
            matchBrackets: true,
            extraKeys: {
                "Tab": function(cm) {
                    if (cm.somethingSelected()) {
                        cm.indentSelection("add");
                    } else {
                        cm.replaceSelection("    ", "end");
                    }
                },
                "Shift-Tab": function(cm) {
                    cm.indentSelection("subtract");
                }
            },
            value: lessonConfig.defaultCode
        });
        
        // Устанавливаем размер редактора
        codeEditor.setSize('100%', '400px');
        
        // Делаем редактор доступным глобально для отладки
        window.codeEditor = codeEditor;
        
        console.log('initEditor: CodeMirror успешно инициализирован');
        
    } catch (error) {
        console.error('initEditor: Ошибка при создании CodeMirror:', error);
        
        // Запасной вариант: простой textarea
        editorElement.innerHTML = `
            <div style="color: #666; padding: 10px; background: #f9f9f9; border: 1px solid #ddd;">
                <p><strong>Редактор кода</strong></p>
            </div>
            <textarea id="simple-editor" 
                      style="width:100%; height:400px; font-family: 'Consolas', monospace; padding:10px; border:1px solid #ddd;">
${lessonConfig.defaultCode}
            </textarea>
            <p><small>Используйте это текстовое поле для написания кода</small></p>
        `;
        
        // Создаём простой интерфейс для текстового поля
        window.codeEditor = {
            getValue: function() { 
                const elem = document.getElementById('simple-editor');
                return elem ? elem.value : ''; 
            },
            setValue: function(code) { 
                const elem = document.getElementById('simple-editor');
                if (elem) elem.value = code; 
            }
        };
    }
}

// Инициализация тестовых случаев
function initTestCases() {
    testCases = lessonConfig.testCases || [];
    
    console.log('initTestCases: загружено тестов', testCases.length);
    
    // Обновляем счетчик тестов
    const testCountElement = document.getElementById('test-count');
    if (testCountElement) {
        testCountElement.textContent = `Тестов: ${testCases.length}`;
    }
}

// Настройка обработчиков событий
function setupEventListeners() {
    console.log('setupEventListeners: настройка обработчиков');
    
    // Кнопка запуска кода
    const runBtn = document.getElementById('run-btn');
    if (runBtn) {
        runBtn.addEventListener('click', executeCode);
        console.log('setupEventListeners: кнопка "Запустить тесты" подключена');
    } else {
        console.error('setupEventListeners: кнопка #run-btn не найдена');
    }
    
    // Кнопка сброса кода
    const resetBtn = document.getElementById('reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetCode);
    }
    
    // Сохранение кода при потере фокуса редактора
    if (codeEditor && codeEditor.on) {
        codeEditor.on('blur', function() {
            saveCodeToStorage();
        });
    }
}

// Функция выполнения кода
async function executeCode() {
    console.log('executeCode: начало выполнения');
    
    const code = window.codeEditor ? window.codeEditor.getValue() : '';
    const runBtn = document.getElementById('run-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const testResults = document.getElementById('test-results');
    
    if (!code.trim()) {
        alert('Введите код для выполнения');
        return;
    }
    
    console.log('executeCode: код получен, длина', code.length);
    
    // Блокируем кнопку и показываем индикатор загрузки
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = 'Выполнение...';
    }
    if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
    }
    
    // Очищаем предыдущие результаты
    if (testResults) {
        testResults.innerHTML = '';
    }
    
    let passedTests = 0;
    let failedTests = 0;
    const startTime = performance.now();
    
    // Запускаем все тесты последовательно
    for (let i = 0; i < testCases.length; i++) {
        const testCase = testCases[i];
        
        try {
            console.log(`executeCode: запуск теста ${i + 1}`, testCase);
            const result = await runSingleTest(code, testCase.input);
            const testPassed = compareOutput(result, testCase.output);
            
            // Создаем элемент результата теста
            const testElement = createTestResultElement(testCase, result, testPassed, i + 1);
            if (testResults) {
                testResults.appendChild(testElement);
            }
            
            if (testPassed) {
                passedTests++;
            } else {
                failedTests++;
            }
            
        } catch (error) {
            console.error(`executeCode: ошибка в тесте ${i + 1}:`, error);
            // Обработка ошибок выполнения
            const errorElement = createTestErrorElement(testCase, error.message, i + 1);
            if (testResults) {
                testResults.appendChild(errorElement);
            }
            failedTests++;
        }
    }
    
    const endTime = performance.now();
    const executionTime = (endTime - startTime) / 1000;
    
    console.log(`executeCode: результаты - пройдено: ${passedTests}, не пройдено: ${failedTests}`);
    
    // Обновляем статистику
    updateTestStats(passedTests, failedTests, executionTime);
    
    // Проверяем, пройдены ли все тесты
    if (passedTests === testCases.length && testCases.length > 0) {
        console.log('executeCode: все тесты пройдены!');
        showCompletionSection();
        
        // Автоматически заполняем поле с кодом для отправки формы
        const finalCodeInput = document.getElementById('final-code-input');
        if (finalCodeInput && window.codeEditor) {
            finalCodeInput.value = window.codeEditor.getValue();
        }
    }
    
    // Восстанавливаем кнопку и скрываем индикатор
    if (runBtn) {
        runBtn.disabled = false;
        runBtn.textContent = '▶ Запустить тесты';
    }
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
    
    // Сохраняем код в localStorage
    saveCodeToStorage();
}

// Запуск одного теста
async function runSingleTest(code, inputData) {
    console.log('runSingleTest: отправка запроса на выполнение');
    
    try {
        const response = await fetch(lessonConfig.apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code: code,
                input: inputData,
                language: 'python'
            })
        });
        
        console.log('runSingleTest: ответ получен, статус', response.status);
        
        if (!response.ok) {
            throw new Error(`Ошибка сервера: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('runSingleTest: результат', result);
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        return result.output || '';
        
    } catch (error) {
        console.error('runSingleTest: ошибка запроса:', error);
        throw error;
    }
}

// Сравнение вывода с ожидаемым результатом
function compareOutput(actual, expected) {
    // Нормализуем строки: убираем лишние пробелы и переводы строк
    const normalize = (str) => {
        if (typeof str !== 'string') return '';
        return str.trim().replace(/\r\n/g, '\n').replace(/\s+/g, ' ');
    };
    
    return normalize(actual) === normalize(expected);
}

// Создание элемента результата теста
function createTestResultElement(testCase, actualOutput, passed, testNumber) {
    const element = document.createElement('div');
    element.className = `test-result ${passed ? 'test-passed' : 'test-failed'}`;
    
    const statusIcon = passed ? '✅' : '❌';
    const statusText = passed ? 'Пройдено' : 'Не пройдено';
    
    element.innerHTML = `
        <div class="test-result-header">
            <span class="test-number">Тест #${testNumber}</span>
            <span class="test-status">${statusIcon} ${statusText}</span>
        </div>
        <div class="test-result-content">
            <div class="test-io">
                <div class="io-section">
                    <strong>Входные данные:</strong>
                    <pre>${testCase.input || '(пусто)'}</pre>
                </div>
                <div class="io-section">
                    <strong>Ожидаемый вывод:</strong>
                    <pre>${testCase.output}</pre>
                </div>
                <div class="io-section">
                    <strong>Ваш вывод:</strong>
                    <pre class="${passed ? 'output-correct' : 'output-incorrect'}">${actualOutput || '(пусто)'}</pre>
                </div>
            </div>
            ${testCase.description ? `<div class="test-description">${testCase.description}</div>` : ''}
        </div>
    `;
    
    return element;
}

// Создание элемента ошибки теста
function createTestErrorElement(testCase, errorMessage, testNumber) {
    const element = document.createElement('div');
    element.className = 'test-result test-error';
    
    element.innerHTML = `
        <div class="test-result-header">
            <span class="test-number">Тест #${testNumber}</span>
            <span class="test-status">❌ Ошибка выполнения</span>
        </div>
        <div class="test-result-content">
            <div class="test-io">
                <div class="io-section">
                    <strong>Входные данные:</strong>
                    <pre>${testCase.input || '(пусто)'}</pre>
                </div>
                <div class="io-section">
                    <strong>Ошибка:</strong>
                    <pre class="error-message">${errorMessage}</pre>
                </div>
            </div>
        </div>
    `;
    
    return element;
}

// Обновление статистики тестов
function updateTestStats(passed, failed, time) {
    const passedElement = document.getElementById('passed-count');
    const failedElement = document.getElementById('failed-count');
    const timeElement = document.getElementById('execution-time');
    
    if (passedElement) {
        passedElement.textContent = `✅ Пройдено: ${passed}`;
    }
    if (failedElement) {
        failedElement.textContent = `❌ Не пройдено: ${failed}`;
    }
    if (timeElement) {
        const timeValue = document.getElementById('time-value');
        if (timeValue) {
            timeValue.textContent = time.toFixed(2);
        }
        timeElement.style.display = 'block';
    }
}

// Показать секцию завершения
function showCompletionSection() {
    const completionSection = document.getElementById('completion-section');
    if (completionSection) {
        completionSection.style.display = 'block';
        console.log('showCompletionSection: секция завершения показана');
        
        // Прокручиваем к секции завершения
        completionSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// Показать сообщение о пройденном уроке
function showCompletionMessage() {
    isLessonCompleted = true;
    const runBtn = document.getElementById('run-btn');
    const completionSection = document.getElementById('completion-section');
    
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = '✅ Урок пройден';
    }
    
    if (completionSection) {
        completionSection.style.display = 'block';
        completionSection.innerHTML = `
            <div class="success-message">
                <h3>🎉 Урок уже пройден!</h3>
                <p>Вы успешно завершили этот урок ранее.</p>
                <a href="/courses" class="btn btn-primary">Вернуться к курсам</a>
            </div>
        `;
    }
}

// Сброс кода к исходному состоянию
function resetCode() {
    if (confirm('Вы уверены, что хотите сбросить код к исходному состоянию?')) {
        if (window.codeEditor) {
            window.codeEditor.setValue(lessonConfig.defaultCode);
        }
        
        // Очищаем результаты
        const testResults = document.getElementById('test-results');
        if (testResults) {
            testResults.innerHTML = '<div class="empty-results"><p>Запустите код, чтобы увидеть результаты тестирования</p></div>';
        }
        
        // Сбрасываем статистику
        updateTestStats(0, 0, 0);
        const timeElement = document.getElementById('execution-time');
        if (timeElement) {
            timeElement.style.display = 'none';
        }
        
        // Скрываем секцию завершения
        const completionSection = document.getElementById('completion-section');
        if (completionSection && !isLessonCompleted) {
            completionSection.style.display = 'none';
        }
    }
}

// Сохранение кода в localStorage
function saveCodeToStorage() {
    if (window.codeEditor) {
        const code = window.codeEditor.getValue();
        const storageKey = `pyway_lesson_${lessonConfig.lessonId}_code`;
        localStorage.setItem(storageKey, code);
        console.log('saveCodeToStorage: код сохранён в localStorage');
    }
}

// Загрузка кода из localStorage
function loadCodeFromStorage() {
    const storageKey = `pyway_lesson_${lessonConfig.lessonId}_code`;
    const savedCode = localStorage.getItem(storageKey);
    
    if (savedCode && savedCode !== lessonConfig.defaultCode && window.codeEditor) {
        // Не спрашиваем подтверждения, просто загружаем
        window.codeEditor.setValue(savedCode);
        console.log('loadCodeFromStorage: код загружен из localStorage');
    }
}