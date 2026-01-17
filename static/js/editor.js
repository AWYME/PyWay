/**
 * Редактор кода для PyWay с системой автоматического тестирования
 * Аналогичен редактору в Яндекс.Учебнике
 */

// Глобальные переменны редактора
let codeEditor;
let testCases = [];
let isLessonCompleted = false;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initEditor();
    initTestCases();
    setupEventListeners();
    
    // Если урок уже пройден, показываем сообщение
    if (lessonConfig.isCompleted) {
        showCompletionMessage();
    }
});

// Инициализация CodeMirror редактора
function initEditor() {
    codeEditor = CodeMirror(document.getElementById('code-editor'), {
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
            "Ctrl-Space": "autocomplete",
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
}

// Инициализация тестовых случаев
function initTestCases() {
    testCases = lessonConfig.testCases || [
        {
            id: 1,
            input: "5\n3",
            output: "8",
            description: "Сложение двух чисел"
        },
        {
            id: 2,
            input: "10\n-2",
            output: "8",
            description: "Сложение положительного и отрицательного"
        },
        {
            id: 3,
            input: "0\n0",
            output: "0",
            description: "Сложение нулей"
        }
    ];
    
    // Отображаем тестовые случаи в таблице
    const testCasesList = document.getElementById('test-cases-list');
    testCasesList.innerHTML = '';
    
    testCases.forEach((testCase, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div class="test-case-input">${testCase.input.replace(/\n/g, '<br>')}</div>
                <small>${testCase.description || `Тест ${index + 1}`}</small>
            </td>
            <td>
                <div class="test-case-output">${testCase.output}</div>
            </td>
        `;
        testCasesList.appendChild(row);
    });
    
    // Обновляем счетчик тестов
    document.getElementById('test-count').textContent = `Тестов: ${testCases.length}`;
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Кнопка запуска кода
    document.getElementById('run-btn').addEventListener('click', executeCode);
    
    // Кнопка сброса кода
    document.getElementById('reset-btn').addEventListener('click', resetCode);
    
    // Сохранение кода при потере фокуса редактора
    codeEditor.on('blur', function() {
        saveCodeToStorage();
    });
}

// Функция выполнения кода
async function executeCode() {
    const code = codeEditor.getValue();
    const runBtn = document.getElementById('run-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const testResults = document.getElementById('test-results');
    
    // Блокируем кнопку и показываем индикатор загрузки
    runBtn.disabled = true;
    runBtn.textContent = 'Выполнение...';
    loadingIndicator.style.display = 'flex';
    
    // Очищаем предыдущие результаты
    testResults.innerHTML = '';
    
    let passedTests = 0;
    let failedTests = 0;
    const startTime = performance.now();
    
    // Запускаем все тесты последовательно
    for (let i = 0; i < testCases.length; i++) {
        const testCase = testCases[i];
        
        try {
            const result = await runSingleTest(code, testCase.input);
            const testPassed = compareOutput(result, testCase.output);
            
            // Создаем элемент результата теста
            const testElement = createTestResultElement(testCase, result, testPassed, i + 1);
            testResults.appendChild(testElement);
            
            if (testPassed) {
                passedTests++;
            } else {
                failedTests++;
            }
            
        } catch (error) {
            // Обработка ошибок выполнения
            const errorElement = createTestErrorElement(testCase, error.message, i + 1);
            testResults.appendChild(errorElement);
            failedTests++;
        }
    }
    
    const endTime = performance.now();
    const executionTime = (endTime - startTime) / 1000;
    
    // Обновляем статистику
    updateTestStats(passedTests, failedTests, executionTime);
    
    // Проверяем, пройдены ли все тесты
    if (passedTests === testCases.length && testCases.length > 0) {
        showCompletionSection();
    }
    
    // Восстанавливаем кнопку и скрываем индикатор
    runBtn.disabled = false;
    runBtn.textContent = '▶ Запустить код';
    loadingIndicator.style.display = 'none';
    
    // Сохраняем код в localStorage
    saveCodeToStorage();
}

// Запуск одного теста
async function runSingleTest(code, inputData) {
    // Используем сервис Judge0 для безопасного выполнения кода
    // В реальном проекте нужно использовать свой серверный endpoint
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
    
    if (!response.ok) {
        throw new Error('Ошибка при выполнении кода');
    }
    
    const result = await response.json();
    
    if (result.error) {
        throw new Error(result.error);
    }
    
    return result.output || '';
}

// Сравнение вывода с ожидаемым результатом
function compareOutput(actual, expected) {
    // Нормализуем строки: убираем лишние пробелы и переводы строк
    const normalize = (str) => str.trim().replace(/\r\n/g, '\n').replace(/\s+/g, ' ');
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
                    <pre>${testCase.input}</pre>
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
                    <pre>${testCase.input}</pre>
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
    document.getElementById('passed-count').textContent = `✅ Пройдено: ${passed}`;
    document.getElementById('failed-count').textContent = `❌ Не пройдено: ${failed}`;
    
    const timeElement = document.getElementById('execution-time');
    document.getElementById('time-value').textContent = time.toFixed(2);
    timeElement.style.display = 'block';
}

// Показать секцию завершения
function showCompletionSection() {
    const completionSection = document.getElementById('completion-section');
    completionSection.style.display = 'block';
    
    // Прокручиваем к секции завершения
    completionSection.scrollIntoView({ behavior: 'smooth' });
}

// Показать сообщение о пройденном уроке
function showCompletionMessage() {
    isLessonCompleted = true;
    document.getElementById('run-btn').disabled = true;
    document.getElementById('run-btn').textContent = '✅ Урок пройден';
    
    const completionSection = document.getElementById('completion-section');
    completionSection.style.display = 'block';
    
    // Заменяем текст в секции завершения
    const successMessage = completionSection.querySelector('.success-message');
    successMessage.innerHTML = `
        <h3>🎉 Урок уже пройден!</h3>
        <p>Вы успешно завершили этот урок ранее.</p>
        <a href="/courses" class="btn btn-primary">Вернуться к курсам</a>
    `;
}

// Сброс кода к исходному состоянию
function resetCode() {
    if (confirm('Вы уверены, что хотите сбросить код к исходному состоянию?')) {
        codeEditor.setValue(lessonConfig.defaultCode);
        codeEditor.focus();
        
        // Очищаем результаты
        document.getElementById('test-results').innerHTML = 
            '<div class="empty-results"><p>Запустите код, чтобы увидеть результаты тестирования</p></div>';
        
        // Сбрасываем статистику
        document.getElementById('passed-count').textContent = '✅ Пройдено: 0';
        document.getElementById('failed-count').textContent = '❌ Не пройдено: 0';
        document.getElementById('execution-time').style.display = 'none';
        
        // Скрываем секцию завершения (если была показана)
        if (!isLessonCompleted) {
            document.getElementById('completion-section').style.display = 'none';
        }
    }
}

// Сохранение кода в localStorage
function saveCodeToStorage() {
    const code = codeEditor.getValue();
    const storageKey = `pyway_lesson_${lessonConfig.lessonId}_code`;
    localStorage.setItem(storageKey, code);
}

// Загрузка кода из localStorage
function loadCodeFromStorage() {
    const storageKey = `pyway_lesson_${lessonConfig.lessonId}_code`;
    const savedCode = localStorage.getItem(storageKey);
    if (savedCode && savedCode !== lessonConfig.defaultCode) {
        if (confirm('Найден сохраненный код. Загрузить его?')) {
            codeEditor.setValue(savedCode);
        }
    }
}