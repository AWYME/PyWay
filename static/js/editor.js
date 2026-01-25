let codeEditor;
let testCases = [];
let isLessonCompleted = false;

const lessonConfig = window.lessonConfig || {
    lessonId: 0,
    defaultCode: '# Напишите ваш код здесь\n# Используйте print() для вывода результата',
    testCases: [],
    isCompleted: false,
    apiUrl: '/api/execute'
};

console.log('editor.js: Конфигурация загружена', lessonConfig);
document.addEventListener('DOMContentLoaded', function() {
    console.log('editor.js: DOMContentLoaded');
    
    setTimeout(function() {
        initEditor();
        initTestCases();
        setupEventListeners();
        
        if (lessonConfig.isCompleted) {
            showCompletionMessage();
        }
        
        console.log('editor.js: Инициализация завершена');
    }, 100);
});

function initEditor() {
    console.log('initEditor: начало инициализации');
    
    const editorElement = document.getElementById('code-editor');
    if (!editorElement) {
        console.error('initEditor: Элемент #code-editor не найден!');
        return;
    }
    
    console.log('initEditor: элемент найден, создаём CodeMirror');
    
    try {
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
        
        codeEditor.setSize('100%', '400px');
        
        window.codeEditor = codeEditor;
        
        console.log('initEditor: CodeMirror успешно инициализирован');
        
    } catch (error) {
        console.error('initEditor: Ошибка при создании CodeMirror:', error);
        
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

function initTestCases() {
    testCases = lessonConfig.testCases || [];
    
    console.log('initTestCases: загружено тестов', testCases.length);
    
    const testCountElement = document.getElementById('test-count');
    if (testCountElement) {
        testCountElement.textContent = `Тестов: ${testCases.length}`;
    }
}

function setupEventListeners() {
    console.log('setupEventListeners: настройка обработчиков');
    
    const runBtn = document.getElementById('run-btn');
    if (runBtn) {
        runBtn.addEventListener('click', executeCode);
        console.log('setupEventListeners: кнопка "Запустить тесты" подключена');
    } else {
        console.error('setupEventListeners: кнопка #run-btn не найдена');
    }
    
    const resetBtn = document.getElementById('reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetCode);
    }
    
    if (codeEditor && codeEditor.on) {
        codeEditor.on('blur', function() {
            saveCodeToStorage();
        });
    }
}

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
    
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = 'Выполнение...';
    }
    if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
    }
    
    if (testResults) {
        testResults.innerHTML = '';
    }
    
    let passedTests = 0;
    let failedTests = 0;
    const startTime = performance.now();
    
    for (let i = 0; i < testCases.length; i++) {
        const testCase = testCases[i];
        
        try {
            console.log(`executeCode: запуск теста ${i + 1}`, testCase);
            const result = await runSingleTest(code, testCase.input);
            const testPassed = compareOutput(result, testCase.output);
            
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
    
    updateTestStats(passedTests, failedTests, executionTime);
    
    if (passedTests === testCases.length && testCases.length > 0) {
        console.log('executeCode: все тесты пройдены!');
        showCompletionSection();
        
        const finalCodeInput = document.getElementById('final-code-input');
        if (finalCodeInput && window.codeEditor) {
            finalCodeInput.value = window.codeEditor.getValue();
        }
    }
    
    if (runBtn) {
        runBtn.disabled = false;
        runBtn.textContent = '▶ Запустить тесты';
    }
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
    saveCodeToStorage();
}

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

function compareOutput(actual, expected) {
    const normalize = (str) => {
        if (typeof str !== 'string') return '';
        return str.trim().replace(/\r\n/g, '\n').replace(/\s+/g, ' ');
    };
    
    return normalize(actual) === normalize(expected);
}

function createTestResultElement(testCase, actualOutput, passed, testNumber) {
    const element = document.createElement('div');
    element.className = `test-result ${passed ? 'test-passed' : 'test-failed'}`;
    const statusText = passed ? 'Пройдено' : 'Не пройдено';
    
    element.innerHTML = `
        <div class="test-result-header">
            <span class="test-number">Тест #${testNumber}</span>
            <span class="test-status">${statusText}</span>
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

function createTestErrorElement(testCase, errorMessage, testNumber) {
    const element = document.createElement('div');
    element.className = 'test-result test-error';
    
    element.innerHTML = `
        <div class="test-result-header">
            <span class="test-number">Тест #${testNumber}</span>
            <span class="test-status">Ошибка выполнения</span>
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

function updateTestStats(passed, failed, time) {
    const passedElement = document.getElementById('passed-count');
    const failedElement = document.getElementById('failed-count');
    const timeElement = document.getElementById('execution-time');
    
    if (passedElement) {
        passedElement.textContent = `Пройдено: ${passed}`;
    }
    if (failedElement) {
        failedElement.textContent = `Не пройдено: ${failed}`;
    }
    if (timeElement) {
        const timeValue = document.getElementById('time-value');
        if (timeValue) {
            timeValue.textContent = time.toFixed(2);
        }
        timeElement.style.display = 'block';
    }
}

function showCompletionSection() {
    const completionSection = document.getElementById('completion-section');
    if (completionSection) {
        completionSection.style.display = 'block';
        console.log('showCompletionSection: секция завершения показана');
        completionSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function showCompletionMessage() {
    isLessonCompleted = true;
    const runBtn = document.getElementById('run-btn');
    const completionSection = document.getElementById('completion-section');
    
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = 'Урок пройден';
    }
    
    if (completionSection) {
        completionSection.style.display = 'block';
        completionSection.innerHTML = `
            <div class="success-message">
                <h3>Урок уже пройден!</h3>
                <p>Вы успешно завершили этот урок ранее.</p>
                <a href="/courses" class="btn btn-primary">Вернуться к курсам</a>
            </div>
        `;
    }
}

function resetCode() {
    if (confirm('Вы уверены, что хотите сбросить код к исходному состоянию?')) {
        if (window.codeEditor) {
            window.codeEditor.setValue(lessonConfig.defaultCode);
        }
        
        const testResults = document.getElementById('test-results');
        if (testResults) {
            testResults.innerHTML = '<div class="empty-results"><p>Запустите код, чтобы увидеть результаты тестирования</p></div>';
        }
        
        updateTestStats(0, 0, 0);
        const timeElement = document.getElementById('execution-time');
        if (timeElement) {
            timeElement.style.display = 'none';
        }
        
        const completionSection = document.getElementById('completion-section');
        if (completionSection && !isLessonCompleted) {
            completionSection.style.display = 'none';
        }
    }
}

function saveCodeToStorage() {
    if (window.codeEditor) {
        const code = window.codeEditor.getValue();
        const storageKey = `pyway_lesson_${lessonConfig.lessonId}_code`;
        localStorage.setItem(storageKey, code);
        console.log('saveCodeToStorage: код сохранён в localStorage');
    }
}

function loadCodeFromStorage() {
    const storageKey = `pyway_lesson_${lessonConfig.lessonId}_code`;
    const savedCode = localStorage.getItem(storageKey);
    
    if (savedCode && savedCode !== lessonConfig.defaultCode && window.codeEditor) {
        window.codeEditor.setValue(savedCode);
        console.log('loadCodeFromStorage: код загружен из localStorage');
    }
}