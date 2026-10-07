import java.util.Arrays;
import java.util.List;

public class NamesTest {
    public static void main(String[] args) {
        List<String> input = Arrays.asList(" Ada ", null, "ada", "", "BOB", " bob ");
        List<String> result = Names.uniqueNames(input);
        if (!result.equals(List.of("Ada", "BOB"))) throw new AssertionError(result);
        if (!input.get(0).equals(" Ada ")) throw new AssertionError("input changed");
        result.add("New");
    }
}
