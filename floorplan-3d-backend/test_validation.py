from schema import SceneGraph, Wall, Door, Room
from validation import validate_and_repair_scene

def run_tests():
    print("Running Validation Tests...")
    
    # 1. Setup mock scene with intentional errors
    sg = SceneGraph()
    
    # Very short wall
    sg.walls.append(Wall(id="w_short", start=(0,0), end=(0, 0.005)))
    
    # Normal wall
    sg.walls.append(Wall(id="w1", start=(1,1), end=(1, 5)))
    
    # Door slightly off the wall (should snap)
    sg.doors.append(Door(id="d1", wall_id="w1", center=(1.05, 3)))
    
    # Door too far (should error)
    sg.doors.append(Door(id="d2", wall_id="w1", center=(1.5, 3)))
    
    # Room with self-intersecting polygon
    sg.rooms.append(Room(id="r_invalid", type="Bedroom", polygon=[(0,0), (0,2), (2,0), (2,2)]))
    
    # 2. Run validation
    corrected_sg, report = validate_and_repair_scene(sg)
    
    # 3. Print report
    print("\nValidation Report:")
    for msg in report:
        print(msg)
        
    print("\nCorrected Values:")
    print(f"w_short length: {corrected_sg.walls[0].length}")
    print(f"d1 center (snapped): {corrected_sg.doors[0].center}")
    print(f"r_invalid area: {corrected_sg.rooms[0].area}")

if __name__ == "__main__":
    run_tests()
