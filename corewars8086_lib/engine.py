import os
import glob
import subprocess
import time
import shutil
import tempfile
from py4j.java_gateway import JavaGateway, GatewayParameters

class CoreWarsEngine:
    def __init__(self, install_dir="build/install/corewars8086"):
        self.process = None
        self.gateway = None
        self.competition = None
        self._managed_dir = tempfile.mkdtemp()
        
        lib_dir = os.path.join(install_dir, "lib")
        jars = glob.glob(os.path.join(lib_dir, "*.jar"))
        if not jars:
            # Fallback to absolute path if relative fails
            abs_lib_dir = os.path.abspath(lib_dir)
            jars = glob.glob(os.path.join(abs_lib_dir, "*.jar"))
            if not jars:
                raise RuntimeError(f"No JARs found in {lib_dir}. Did you run 'gradle installDist'?")
        
        classpath = os.pathsep.join(jars)
        
        java_cmd = "java"
        # Prefer JAVA_HOME
        java_home = os.environ.get("JAVA_HOME")
        if java_home and os.path.exists(os.path.join(java_home, "bin", "java.exe")):
             java_cmd = os.path.join(java_home, "bin", "java.exe")
        elif shutil.which("java"):
             java_cmd = "java"
        else:
             raise RuntimeError("Java executable not found in PATH or JAVA_HOME")

        # Start Java process
        cmd = [java_cmd, "-cp", classpath, "il.co.codeguru.corewars8086.Py4JEntryPoint"]
        # We can redirect stdout/stderr if needed, but for debugging it's useful to see
        self.process = subprocess.Popen(cmd)
        
        # Connect to gateway (retry a few times)
        retries = 20
        last_error = None
        for i in range(retries):
            try:
                self.gateway = JavaGateway(gateway_parameters=GatewayParameters(auto_convert=True))
                # Test connection
                self.gateway.jvm.java.lang.System.currentTimeMillis()
                last_error = None
                break
            except Exception as e:
                last_error = e
                time.sleep(0.5)
        
        if last_error:
            self.terminate_process()
            raise RuntimeError(f"Failed to connect to Py4J Gateway: {last_error}")

    def load_warriors(self, warrior_dir, zombies_dir=None, results_file="scores.csv"):
        Options = self.gateway.jvm.il.co.codeguru.corewars8086.cli.Options
        OptionsClass = self.gateway.jvm.java.lang.Class.forName("il.co.codeguru.corewars8086.cli.Options")
        OptionsParser = self.gateway.jvm.com.google.devtools.common.options.OptionsParser
        Competition = self.gateway.jvm.il.co.codeguru.corewars8086.war.Competition
        
        parser = OptionsParser.newOptionsParser(OptionsClass)
        
        args = ["--warriorsDir", os.path.abspath(warrior_dir)]
        if zombies_dir:
            args.extend(["--zombiesDir", os.path.abspath(zombies_dir)])
        
        if results_file:
            args.extend(["--outputFile", os.path.abspath(results_file)])
        
        java_args = self.gateway.new_array(self.gateway.jvm.java.lang.String, len(args))
        for i, arg in enumerate(args):
            java_args[i] = arg
            
        parser.parseAndExitUponError(java_args)
        options = parser.getOptions(OptionsClass)
        
        try:
            self.competition = Competition(options)
        except Exception as e:
            # Re-raise exception with better message if possible, or just let it propagate
            raise
    
    def add_warrior_from_bytes(self, name, data):
        path = os.path.join(self._managed_dir, name)
        with open(path, "wb") as f:
            f.write(data)
        
        # Invalidate current competition so it reloads on next run
        self.competition = None

    def get_warrior_count(self):
        if not self.competition:
            # If competition not loaded but we have managed warriors, count files?
            # Or just return 0. For consistency with Java behavior, 0 is safer until loaded.
            return 0
        return self.competition.getWarriorRepository().getNumberOfGroups()

    def run_competition(self, battles=100, combination_size=4, parallel=True, threads=4):
        if not self.competition:
             # Try to auto-load from managed dir if not explicitly loaded
             if os.listdir(self._managed_dir):
                 self.load_warriors(self._managed_dir)
             else:
                 raise RuntimeError("Warriors not loaded. Call load_warriors() or add_warrior_from_bytes() first.")
             
        try:
            if parallel:
                self.competition.runCompetitionInParallel(battles, combination_size, threads)
            else:
                self.competition.runCompetition(battles, combination_size, False)
        except Exception as e:
            if hasattr(e, 'java_exception'):
                print("Java Error:", e.java_exception.toString())
                try:
                    for el in e.java_exception.getStackTrace():
                        print("\tat", el.toString())
                except:
                    pass
                if e.java_exception.getCause():
                    print("Cause:", e.java_exception.getCause().toString())
            raise

    def get_scores(self):
        if not self.competition:
            return []
        
        repo = self.competition.getWarriorRepository()
        groups = repo.getWarriorGroups()
        
        results = []
        for i in range(groups.size()):
            group = groups.get(i)
            group_data = {
                "name": group.getName(),
                "score": group.getGroupScore(),
                "warriors": []
            }
            
            warriors = group.getWarriors()
            scores = group.getScores()
            for j in range(warriors.size()):
                w_data = warriors.get(j)
                w_score = scores.get(j)
                group_data["warriors"].append({
                    "name": w_data.getName(),
                    "score": w_score
                })
            results.append(group_data)
            
        # Sort by score desc
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def terminate_process(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        
        # Cleanup managed dir
        if self._managed_dir and os.path.exists(self._managed_dir):
            try:
                shutil.rmtree(self._managed_dir)
            except OSError:
                pass

    def close(self):
        if self.gateway:
            self.gateway.shutdown()
            self.gateway = None
        self.terminate_process()
        
    def __del__(self):
        self.close()
