import argparse
from pcb_part_finder.core.queue import process_queue
from pcb_part_finder.api.api import app
from pcb_part_finder.web.server import app as web_app

def main():
    parser = argparse.ArgumentParser(description='PCB Part Finder')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Queue processor command
    queue_parser = subparsers.add_parser('queue', help='Run the queue processor')
    
    # API server command
    api_parser = subparsers.add_parser('api', help='Run the API server')
    api_parser.add_argument('--host', default='localhost', help='Host to bind to')
    api_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    
    # Web server command
    web_parser = subparsers.add_parser('web', help='Run the web server')
    web_parser.add_argument('--host', default='localhost', help='Host to bind to')
    web_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    
    args = parser.parse_args()
    
    if args.command == 'queue':
        process_queue()
    elif args.command == 'api':
        import uvicorn
        uvicorn.run(app, host=args.host, port=args.port)
    elif args.command == 'web':
        import uvicorn
        uvicorn.run(web_app, host=args.host, port=args.port)
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 