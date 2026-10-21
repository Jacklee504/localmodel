import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class NamesHiddenTest {
    public static void main(String[] args) {
        List<String> input = new ArrayList<>(Arrays.asList("bob", "  BOB  ", "Bob"));
        List<String> result = Names.uniqueNames(input);
        if (!result.equals(List.of("bob"))) throw new AssertionError(result);

        List<String> empty = new ArrayList<>();
        if (!Names.uniqueNames(empty).isEmpty()) throw new AssertionError("not empty");

        List<String> onlyBlanks = new ArrayList<>(Arrays.asList("", "   ", null));
        if (!Names.uniqueNames(onlyBlanks).isEmpty()) throw new AssertionError("not empty");

        if (input.size() != 3) throw new AssertionError("input size changed");
        if (!input.get(0).equals("bob")) throw new AssertionError("input changed");
    }
}
