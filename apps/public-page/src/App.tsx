import { useState, useRef, useCallback } from 'react';
import { Button } from '@edulution-io/ui-kit';
import { Card, CardContent, Input } from '@shared-ui';

const INSTALL_COMMAND = 'bash <(curl -s https://get.edulution.io/installer)';

const App = () => {
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(INSTALL_COMMAND);
    } catch {
      if (inputRef.current) {
        inputRef.current.select();
        inputRef.current.setSelectionRange(0, 99999);
        document.execCommand('copy');
      }
    }

    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const handleInputClick = useCallback(() => {
    inputRef.current?.select();
  }, []);

  return (
    <div className="page-wrapper">
      <Card variant="modal">
        <CardContent className="flex flex-col items-center gap-6 p-0">
          <a
            href="https://edulution.io"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img
              src="/img/edulution.io_INSTALLER.svg"
              alt="edulution.io User Interface Logo"
              className="logo"
            />
          </a>

          <div className="w-full">
            <h2 className="mb-4 text-center text-lg font-semibold text-background">Quick Install</h2>

            <div className="mb-5">
              <Input
                ref={inputRef}
                type="text"
                variant="login"
                value={INSTALL_COMMAND}
                readOnly
                onClick={handleInputClick}
                aria-label="Installation command"
                className="font-mono text-sm shadow-md"
              />
            </div>

            <Button
              variant="btn-security"
              size="lg"
              className="mx-auto w-full justify-center text-white shadow-xl"
              onClick={handleCopy}
            >
              {copied ? '\u2713 Kopiert!' : 'In Zwischenablage kopieren'}
            </Button>

            <div
              className={`copy-feedback ${copied ? 'show' : ''}`}
              role="status"
              aria-live="polite"
            >
              {copied ? 'In die Zwischenablage kopiert!' : ''}
            </div>
          </div>

          <div className="footer-section w-full">
            Alle Informationen auf{' '}
            <a
              href="https://edulution.io"
              target="_blank"
              rel="noopener noreferrer"
            >
              edulution.io
            </a>{' '}
            oder in der{' '}
            <a
              href="https://docs.edulution.io"
              target="_blank"
              rel="noopener noreferrer"
            >
              Dokumentation
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default App;
