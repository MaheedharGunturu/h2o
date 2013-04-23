package water;
import jsr166y.CountedCompleter;

/** Map/Reduce style distributed computation. */
public abstract class MRTask extends DRemoteTask {

  transient private int _lo, _hi; // Range of keys to work on
  transient private MRTask _left, _rite; // In-progress execution tree

  transient boolean done = false;
  static final long log2(long x){
    long y = x >> 1;
    while(y > 0){
      x = y;
      y = x >> 1;
    }
    return x > 0?y+1:y;
  }

  public void init() {
    _lo = 0;
    _hi = _keys.length;
    long reqMem = (log2(_hi - _lo)+2)*memOverheadPerChunk();
    MemoryManager.reserveTaskMem(reqMem); // min. memory required to run at least single threaded
    _reservedMem = reqMem;
  }

  /** Run some useful function over this <strong>local</strong> key, and
   * record the results in the <em>this<em> MRTask. */
  abstract public void map( Key key );

  transient long _reservedMem;
  /** Do all the keys in the list associated with this Node.  Roll up the
   * results into <em>this<em> MRTask. */
  @Override public final void localCompute() {
    assert isLocalCompute();
    if( _hi-_lo >= 2 ) { // Multi-key case: just divide-and-conquer to 1 key
      final int mid = (_lo+_hi)>>>1; // Mid-point
      assert _left == null && _rite == null;
      MRTask l = (MRTask)clone();
      MRTask r = (MRTask)clone();
      (_left = l)._reservedMem = 0;
      (_rite = r)._reservedMem = 0;
      _left._hi = mid;          // Reset mid-point
      _rite._lo = mid;          // Also set self mid-point
      assert _left.isLocalCompute();
      assert _rite.isLocalCompute();
      setPendingCount(1);
      // compute min. memory required to run the right branch in parallel
      // min memory equals to the max memory used if the right branch will be executed single threaded (but in parallel with our left branch)
      // assuming all memory is kept in the tasks and it is halved by reduce operation, the min memory is proportional to the depth of the right subtree.
      long reqMem = (_hi - _lo) > 2?(log2(_hi - mid)+1)*memOverheadPerChunk():0;
//      _left.fork();
//      _rite.compute2();
      if(reqMem == 0 || MemoryManager.tryReserveTaskMem(reqMem)){
        _reservedMem += reqMem;   // Remember the amount of reserved memory to free it later.
        assert _left != _rite;
        H2O.submitTask(_left);             // Runs in another thread/FJ instance
        _rite.localCompute();             // Runs in another thread/FJ instance
      } else {
        assert _left != _rite;
        _left.localCompute();
        _rite.localCompute();
      }
    } else {
      if( _hi > _lo ) {          // Single key?
        map(_keys[_lo]);        // Get it, run it locally
      }
      tryComplete();              // And this task is complete
    }
  }

  private final void returnReservedMemory(){
    if(_reservedMem > 0)MemoryManager.freeTaskMem(_reservedMem);
  }

  @Override public final void onLocalCompletion() {
    assert !done;
    done = true;
    // Reduce results into 'this' so they collapse going up the execution tree.
    // NULL out child-references so we don't accidentally keep large subtrees
    // alive: each one may be holding large partial results.
    if( _left != null ) reduceAlsoBlock(_left); _left = null;
    if( _rite != null ) reduceAlsoBlock(_rite); _rite = null;
    returnReservedMemory();
  }
  @Override public final boolean onExceptionalCompletion(Throwable ex, CountedCompleter caller ) {
    _left = null;
    _rite = null;
    returnReservedMemory();
    return super.onExceptionalCompletion(ex, caller);
  }
}
